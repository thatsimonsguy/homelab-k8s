# Traceroute closed-trial requests

The marketing site at `https://traceroutehealth.com` (chart `apps/traceroute-site`, source
`ismatthealthy/site/`) has an "Ask to join" form. It posts URL-encoded `subject` and `body`
fields to `https://traceroutehealth.com/trial-request`; this chart's ingress routes that
path to Mailform, whose target `trial-request.json` (SealedSecret
`mailform-traceroute-trial-targets`, `templates/traceroute-trial.sealed.yaml`) emails
Matt's inbox with subject prefix `[Traceroute trial]`.

The target reuses the contact form's sender and SMTP transport, accepts only requests
whose `Origin` is exactly `https://traceroutehealth.com`, and limits each source IP to
5 requests per hour in memory. It has no bearer key: it is a public form, like `/contact`.
Nothing is stored anywhere; the email is the record. The relay returns 200 after SMTP
acceptance, 403 for a wrong origin, 422 for a missing subject/body, 429 when rate limited.

Mailform reads targets at startup. Adding the secret to `additionalTargetsSecrets` changes
the pod template, so Argo's sync restarts the pod. To change the recipient, rate limit or
origin, re-seal the target on the K3s host and commit the ciphertext:

```
kubectl create secret generic mailform-traceroute-trial-targets --namespace=mailform \
  --from-file=trial-request.json=/tmp/trial-request.json --dry-run=client -o yaml | kubeseal -o yaml
```

Delivery test from inside the cluster (say that it is a test in the body):

```
kubectl run relay-test --rm -i --restart=Never --image=curlimages/curl -- \
  -s -o /dev/null -w '%{http_code}\n' -X POST http://mailform.mailform.svc.cluster.local:3000/trial-request \
  -H 'Origin: https://traceroutehealth.com' --data-urlencode 'subject=Delivery test' \
  --data-urlencode 'body=<p>Delivery test of the trial-request relay, not a real request.</p>'
```

Public exposure needs the Cloudflare tunnel public hostname `traceroutehealth.com` pointed
at the same Traefik origin as `app.traceroutehealth.com`; the tunnel is remotely managed,
so that is a dashboard change, and it creates the apex DNS record.
