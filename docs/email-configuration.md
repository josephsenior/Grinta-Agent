# Email Configuration Guide

This guide explains how to configure email sending for password reset functionality in Forge.

## Overview

The email service uses SMTP to send transactional emails. It's configured via environment variables and supports any SMTP provider (Gmail, SendGrid, AWS SES, etc.).

## Environment Variables

Set the following environment variables to enable email sending:

```bash
# Required SMTP Configuration
SMTP_HOST=smtp.gmail.com          # SMTP server hostname
SMTP_PORT=587                     # SMTP server port (587 for TLS, 465 for SSL)
SMTP_USER=your-email@gmail.com    # SMTP username (usually your email)
SMTP_PASSWORD=your-app-password   # SMTP password or app-specific password

# Optional Configuration
SMTP_FROM_EMAIL=noreply@forge.ai  # Sender email address (defaults to SMTP_USER)
FRONTEND_URL=http://localhost:3001 # Frontend URL for reset links (defaults to localhost:3001)
```

## Common SMTP Providers

### Gmail

1. Enable 2-factor authentication on your Google account
2. Generate an App Password:
   - Go to Google Account settings
   - Security → 2-Step Verification → App passwords
   - Generate a password for "Mail"
3. Use these settings:

```bash
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-16-char-app-password
```

### SendGrid

```bash
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASSWORD=your-sendgrid-api-key
SMTP_FROM_EMAIL=noreply@yourdomain.com
```

### AWS SES

```bash
SMTP_HOST=email-smtp.us-east-1.amazonaws.com  # Use your region
SMTP_PORT=587
SMTP_USER=your-ses-smtp-username
SMTP_PASSWORD=your-ses-smtp-password
SMTP_FROM_EMAIL=noreply@yourdomain.com
```

### Mailtrap (for testing)

```bash
SMTP_HOST=sandbox.smtp.mailtrap.io
SMTP_PORT=2525
SMTP_USER=your-mailtrap-username
SMTP_PASSWORD=your-mailtrap-password
```

## Testing

1. Set the environment variables in your `.env` file or export them
2. Restart the Forge server
3. Request a password reset from the forgot password page
4. Check your email inbox (or Mailtrap inbox if using Mailtrap)

## Troubleshooting

### Email service not sending emails

- Check that all required environment variables are set
- Verify SMTP credentials are correct
- Check server logs for error messages
- Ensure your SMTP provider allows connections from your server IP
- For Gmail, make sure you're using an App Password, not your regular password

### Emails going to spam

- Configure SPF, DKIM, and DMARC records for your domain
- Use a verified sender email address
- Avoid spam trigger words in email content
- Consider using a dedicated email service like SendGrid or AWS SES

## Development Mode

If SMTP is not configured, the system will:
- Still generate reset tokens
- Log a warning message
- Log the reset token to the console (for testing purposes)
- Return success to prevent email enumeration

This allows development to continue without email configuration, but reset links won't be sent via email.

