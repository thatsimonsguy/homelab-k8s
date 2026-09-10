# Runbook — encrypted data volumes on burdturglar (AGG-377)

Wieser's sandbox data lives on two LUKS2 volumes; everything else on the host
stays on the plain OS SSD. This page is what to do when something about them
needs a human. Design record: Linear AGG-377.

| Volume | Device | Holds |
|---|---|---|
| `/dev/mapper/pgdata` → `/srv/crypt/pgdata` | Samsung PM871b 256 GB (`/dev/disk/by-id/ata-SAMSUNG_SSD_PM871b_2.5_7mm_256GB_S3U4NB0K205248`) | `postgresql/` = the Postgres PV (every database) |
| `/dev/mapper/bulk` → `/srv/crypt/bulk` | WD Red Pro 4 TB (`/dev/disk/by-id/ata-WDC_WD4003FFBX-68MU3N0_VBG9L9RR`) | `minio/`, `aggsys-sandbox-data/` (Titan backups, work dirs, last-good dump) |

The Kubernetes PV host paths under `/var/lib/rancher/k3s/storage/pvc-*` are
**bind mounts** onto those directories (`/etc/fstab`, `_netdev,nofail,
x-systemd.before=k3s.service`). The directories underneath are `chattr +i`, so
a locked volume can never be written in the clear: the pods crash-loop instead.

## How unlocking works

Clevis binds each volume to Tang with an *any one of two* threshold:

- Tang on Matt's desktop — `http://192.168.1.91` (`tangd.socket`, keys in `/var/lib/tang`)
- Tang on the HVAC Pi (`hvac-controller`, ssh alias `rpi`) — `http://192.168.1.48` (same)

On boot, `systemd-cryptsetup@{pgdata,bulk}` asks, `clevis-luks-askpass` answers
through Tang, the volumes mount, then k3s starts. `aggsys-boot-notify.service`
posts the result to the `aggsys-alerts` ntfy topic ~90 s after boot; the
`AggsysEncryptedVolumeMissing` alert fires if either mount is absent for 5 min.
A passphrase keyslot is the fallback. **The passphrase and both LUKS header
backups live in Matt's password manager / cloud storage — nowhere on this host
or the desktop.**

## Both Tang servers unreachable → unlock by hand

```
ssh k3s
sudo cryptsetup open /dev/disk/by-id/ata-SAMSUNG_SSD_PM871b_2.5_7mm_256GB_S3U4NB0K205248 pgdata   # passphrase
sudo cryptsetup open /dev/disk/by-id/ata-WDC_WD4003FFBX-68MU3N0_VBG9L9RR bulk                     # passphrase
sudo mount /srv/crypt/pgdata && sudo mount /srv/crypt/bulk && sudo mount -a
kubectl -n postgresql delete pod postgresql-0
kubectl -n minio rollout restart deploy/minio
kubectl -n aggsys rollout restart deploy/aggsys-erp-server
```

A pod started against the immutable empty directory keeps that view until it
is recreated, hence the restarts. Tang-by-hand (no passphrase) is
`sudo clevis luks unlock -d <device> -n <name>`.

## A Tang host was rebuilt or replaced

Its keys changed, so re-bind (needs the passphrase; run for both devices):

```
sudo clevis luks list -d <device>                 # note the slot number of the sss pin
sudo clevis luks unbind -d <device> -s <slot>     # remove the old binding
sudo clevis luks bind -y -d <device> sss '{"t":1,"pins":{"tang":[{"url":"http://192.168.1.91"},{"url":"http://192.168.1.48"}]}}'
```

Adding a third Tang host is the same bind with a third URL. Tang itself:
`apt install tang && systemctl enable --now tangd.socket`, verify with
`curl http://<host>/adv`.

## Restore a damaged LUKS header

`sudo cryptsetup luksHeaderRestore <device> --header-backup-file <backup>` with
the backup from Matt's cloud storage (16 MiB each, `pgdata.luks-header`,
`bulk.luks-header`). The passphrase keyslot in the backup is the one that was
current when it was taken; Tang bindings made after the backup are lost —
re-bind as above.

## Change the passphrase

`sudo cryptsetup luksChangeKey <device>` on both devices, then take fresh header
backups (`sudo cryptsetup luksHeaderBackup <device> --header-backup-file …`),
move them to the password manager, and shred the local copies.

## Standing rules

- **Anything that leaves this host is encrypted first** (`age -p` or an `age`
  recipient key held in the sealed secret + password manager). Today nothing
  leaves: MinIO backups and reports stay on the `bulk` volume.
- The nightly refuses to run unless its volume resolves to a dm-crypt device
  (`SANDBOX_ALLOW_UNENCRYPTED=1` exists for proof environments only).
- Old work directories and cached Titan backups are pruned after
  `SANDBOX_RETENTION_DAYS` (7) by the nightly's `prune` step.
- Unattended-upgrades reboots at 10:00 UTC (05:00 Central): after the nightly,
  before Wieser's day. The boot notification says whether the volumes unlocked.
- The old OS SSD once held this data in the clear (deleted + `fstrim`
  2026-09-10): secure-erase it on retirement.
- Postgres and MinIO have no LAN address; the workstation uses
  `scripts/dev/homelab-tunnel.sh` (aggsys repo). `pg_hba` is scram-only; the
  sandbox databases are owned by the `quoin_sandbox` role, connect revoked
  from PUBLIC.
