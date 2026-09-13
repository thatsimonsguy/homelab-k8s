# Traceroute trial AWS credentials

These sealed manifests are provisioning inputs, outside ArgoCD application paths.
Do not include the whole directory in a chart or apply all credentials together.
They target namespace `traceroute`; Sealed Secrets ciphertext is bound to the exact
Secret name and namespace. Reseal securely if a deployment contract changes either.

| Manifest | IAM identity | Intended consumer |
| --- | --- | --- |
| `backup-writer.sealed.yaml` | `traceroute-trial-backup-writer` | Nightly backup job only |
| `journal-writer.sealed.yaml` | `traceroute-trial-journal-writer` | Server deletion/revocation journal writes |
| `recovery-reader.sealed.yaml` | `traceroute-trial-recovery-reader` | Manually launched recovery tooling only |

Each Secret contains `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, and `AWS_REGION`.
Do not give the server backup-read access or mount recovery credentials into ongoing
workloads. Restore reconciliation reads the journal and backups; it does not receive
S3 write or deletion permissions through these credentials.

AWS account: `881792194126`; region: `us-east-2`.
Backup bucket: `ismatthealthy-trial-backups-881792194126-us-east-2`.
Journal bucket: `ismatthealthy-trial-journal-881792194126-us-east-2`.

Writers require `If-None-Match: *` when creating objects. Use unique backup keys.
Backup multipart initiation and part upload are permitted; completion must be
conditional. Neither writer can read or delete objects. The recovery reader can
list and read both buckets, including versions, but cannot write or delete.

The identities have no console passwords. The scoped managed policies are permission
grants, not permissions boundaries; do not attach broader policies or group grants.

Rotate by **2026-12-10**, or sooner if the trial ends or a credential is exposed.
This is a maintenance due date, not automatic key expiration. Create a replacement,
reseal it, deploy only to its intended consumer, verify it works, then deactivate
and delete the replaced key. Do not log credentials or put plaintext in Git.

The cluster recovery key is required to decrypt these files after a disaster.
Keep that key in the off-cluster encrypted recovery storage. Workload configuration,
backup uploads and restore rehearsal are separate implementation tasks.

## Kubernetes names and initialization

IAM user names above differ from the Kubernetes Secret names:

| Purpose | Kubernetes Secret |
| --- | --- |
| Backup writer | `traceroute-aws-backup-writer` |
| Journal writer | `traceroute-aws-journal-writer` |
| Recovery reader | `traceroute-aws-recovery-reader` |

The chart includes the backup-writer sealed manifest only for its scheduled backup
job. `publication.enabled` adds the journal-writer sealed manifest and mounts it only
into the product service. Its bucket is `publication.bucket`; the expected account
and independently retained journal UUID share the `backup` values. Disabling
publication removes the service flags/mount and the managed journal SealedSecret.
Wait for Secret removal and the replacement rollout before a recovery journal read.
The recovery-reader manifest remains an explicit operator-only provisioning input.

For initial provisioning only, run `python3 initialize-journal.py --initialize`
from the operator workstation (requires AWS CLI, PyYAML and SSH access to k3s).
It reads the UUID retained in chart values, temporarily unseals the journal writer
and recovery reader, conditionally writes the canonical initialization marker,
verifies its exact bytes using the independent reader, and removes those temporary
cluster credentials. It refuses preexisting provisioning secrets to avoid disturbing
another consumer. No credentials or health payloads are printed. Never invoke this
script during recovery: a missing marker must instead keep restored access closed.
