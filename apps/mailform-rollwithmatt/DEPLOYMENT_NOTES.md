# Mailform Rock-and-Roll Contact Form Integration - COMPLETED ✅

## Changes Made

### 1. Updated Ingress Configuration ✅

Added `api.rollwithmatt.com` to the ingress hosts in `values.yaml` to handle contact form submissions from the rock-and-roll RPG website.

```yaml
hosts:
  - host: matthewpsimons.com
    paths:
      - path: /contact
        pathType: Prefix
  - host: api.rollwithmatt.com  # NEW
    paths:
      - path: /contact
        pathType: Prefix
```

### 2. Enhanced Contact Configuration ✅

Updated the sealed secret with a new contact.json configuration that supports both the existing matthewpsimons.com contact form and the new rock-and-roll RPG contact form with additional fields:

**New Fields Supported:**
- `phone` (optional)
- `discord` (optional) 
- `preferredSystem` (optional) - RPG system preference
- `groupSize` (optional) - Number of players
- `message` (enhanced)

**Updated Configuration:**
- Added `rollwithmatt.com`, `www.rollwithmatt.com`, and `api.rollwithmatt.com` to CORS origins
- Increased rate limit to 5 requests per 5 minutes
- Added field validation for all new RPG-specific fields
- Updated subject prefix to "[Contact Form]" for better identification

### 3. Updated Sealed Secret ✅

Successfully created and deployed a new sealed secret using the existing AWS SES credentials from the k3s cluster.

## Next Steps

### 1. DNS Configuration

Ensure that `api.rollwithmatt.com` points to your Traefik ingress controller. The changes will automatically deploy via ArgoCD once committed.

### 2. Test the Integration

After ArgoCD deploys the changes, test both contact forms:

```bash
# Test the rock-and-roll contact form
curl -X POST https://api.rollwithmatt.com/contact \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Player",
    "email": "test@example.com",
    "preferredSystem": "D&D 5e",
    "groupSize": "4",
    "message": "Test message from rock-and-roll site"
  }'

# Test the existing contact form  
curl -X POST https://matthewpsimons.com/contact \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test User",
    "email": "test@example.com", 
    "message": "Test message"
  }'
```

## Integration Summary

The rock-and-roll RPG website contact form at `ContactSection.tsx:53` is already configured to POST to `https://api.rollwithmatt.com/contact`. Once these changes are deployed:

1. ✅ **Ingress routes** both domains to the mailform service
2. ✅ **Configuration supports** all RPG-specific fields (preferredSystem, groupSize, discord, etc.)
3. ✅ **CORS allows** requests from rollwithmatt.com domains  
4. ✅ **Rate limiting** and validation protect against abuse
5. ✅ **AWS SES credentials** are securely stored as sealed secrets

The contact form should work seamlessly without any changes to the rock-and-roll website code.