# Alerting Integrations: Slack & PagerDuty

Complete guide for setting up Slack and PagerDuty alerting integrations with Forge's monitoring stack.

---

## 📋 **Overview**

Forge has **6 alert groups** with **15+ alert rules** configured in Grafana, but currently alerts only show in the Grafana UI. This guide shows how to add real-time notifications via:

- **Slack** - Team collaboration and channel notifications
- **PagerDuty** - On-call management and incident tracking

---

## 🔔 **What Are Notification Channels?**

### **Simple Explanation**

A **notification channel** is a destination where Grafana sends alerts when they fire. Think of it as a "contact" or "address" for your alerts.

**The Flow:**
```
Alert Rule Fires
    ↓
Grafana checks: "Where should I send this?"
    ↓
Looks at Notification Channels linked to the alert
    ↓
Sends alert to each channel
    ↓
You get notified via Slack, PagerDuty, Email, etc.
```

### **Analogy**

Think of it like phone contacts:
- **Alert Rule** = "When something bad happens"
- **Notification Channel** = "Send a message to this contact"
- The channel defines **how** and **where** to send the alert

### **Examples**

**Example 1: Single Channel**
- Alert: "Service Down"
- Notification Channel: `Slack - Forge Alerts` → Sends to `#forge-alerts` in Slack
- Result: When alert fires, your team sees it in Slack

**Example 2: Multiple Channels**
- Alert: "High Error Rate" (critical)
- Notification Channels:
  - `Slack - Critical` → Sends to `#ops-critical` in Slack
  - `PagerDuty - Critical` → Creates incident in PagerDuty
- Result: When alert fires, team sees it in Slack AND on-call engineer gets paged

### **Types of Notification Channels**

Grafana supports many channel types:

| Channel Type | What It Does | Use Case |
|-------------|--------------|----------|
| **Slack** | Sends message to Slack channel | Team notifications |
| **PagerDuty** | Creates incident in PagerDuty | On-call paging |
| **Email** | Sends email | Email notifications |
| **Webhook** | Sends HTTP POST to URL | Custom integrations |
| **Discord** | Sends to Discord channel | Team chat |
| **Microsoft Teams** | Sends to Teams channel | Enterprise teams |
| **Telegram** | Sends to Telegram chat | Personal notifications |
| **OpsGenie** | Creates alert in OpsGenie | Incident management |

### **Why Multiple Channels?**

Different alerts need different destinations:

```
Critical Alert (Service Down)
  → PagerDuty (wake up on-call engineer)
  → Slack #ops-critical (team awareness)

Warning Alert (Slow Response)
  → Slack #forge-alerts (team notification only)
  → No PagerDuty (not urgent enough to wake someone)

Info Alert (Cost Spike)
  → Slack #forge-info (optional, low priority)
```

### **How It Works**

1. **Create Notification Channel** (one-time setup)
   - Define: Name, Type, Destination (webhook URL, email, etc.)
   - Example: Create `Slack - Forge Alerts` channel pointing to Slack webhook

2. **Link Channel to Alert Rule**
   - Edit alert rule → Add notification channel
   - Select the channel you created
   - Save

3. **When Alert Fires**
   - Grafana automatically sends to all linked channels
   - You get notified in Slack, PagerDuty, Email, etc.

### **Current State in Forge**

**Without Notification Channels:**
```
Alert Fires → ❌ Nowhere (just shows in Grafana UI)
```

**With Notification Channels (after setup):**
```
Alert Fires
    ↓
    ├─→ Slack Channel (#forge-alerts) → 📱 Team sees it
    ├─→ PagerDuty → 📞 On-call engineer gets paged
    └─→ Email → 📧 You get email
```

### **Key Concepts**

- **Notification Channel** = A destination for alerts (Slack, PagerDuty, Email, etc.)
- **Create once, use many times** - Create channels once, then link to multiple alert rules
- **One alert → Multiple channels** - One alert can send to multiple channels
- **Different alerts → Different channels** - Route alerts based on severity/importance
- **Without channels** - Alerts only show in Grafana UI (no external notifications)

**Think of it as:** "When this alert fires, send it to these places."

---

## 🎯 **Current Alert Rules**

Your monitoring stack includes these alert groups:

### **1. Critical Alerts** (`forge-critical-alerts`)
- **High Error Rate** - Error rate >5% for 5 minutes
- **Slow Response Time** - p95 latency >2000ms for 10 minutes
- **Low Cache Hit Rate** - Cache hit rate <30% for 15 minutes
- **EventService RPC Error Rate** - Error rate >5% for 5 minutes
- **RuntimeService RPC Latency** - p95 latency >5s for 10 minutes

### **2. Availability Alerts** (`forge-availability-alerts`)
- **Low Success Rate** - Success rate <95% for 10 minutes
- **Service Down** - Service not responding for 2 minutes
- **High Retry Rate** - Retry rate >20% for 10 minutes

### **3. Cost Alerts** (`forge-cost-alerts`)
- **High Token Usage** - Token rate >1000/sec for 30 minutes

### **4. New Alerts** (`forge-new-alerts`)
- **Low Retry Success Rate** - Retry success <60% for 10 minutes
- **LLM Cost Spike** - Cost 2x above daily average for 15 minutes
- **High CodeAct Failure Rate** - Failure rate >10% for 10 minutes
- **File Edit Failures** - >5 failures in 5 minutes
- **Quota Exceeded** - >10 quota events in 1 hour
- **Database Connection Errors** - >3 errors in 5 minutes

---

## 🔔 **Slack Integration**

### **Benefits**
- ✅ Real-time notifications in Slack channels
- ✅ Rich formatting with context and links
- ✅ Team collaboration via threads
- ✅ @mentions for on-call engineers
- ✅ Link back to Grafana dashboards
- ✅ Easy setup (~15 minutes)

### **Setup Steps**

#### **1. Create Slack Webhook**

1. Go to: https://api.slack.com/apps
2. Click **"Create New App"** → **"From scratch"**
3. Name: `Forge Alerts`
4. Workspace: Select your workspace
5. Click **"Create App"**

6. In left sidebar, click **"Incoming Webhooks"**
7. Toggle **"Activate Incoming Webhooks"** to ON
8. Click **"Add New Webhook to Workspace"**
9. Select channel: `#forge-alerts` (or create new channel)
10. Click **"Allow"**
11. **Copy the Webhook URL** (starts with `https://hooks.slack.com/services/...`)

#### **2. Configure Grafana Notification Channel**

**Option A: Via Grafana UI**

1. Open Grafana: http://localhost:3030
2. Login: `admin` / `forge_admin_2025`
3. Go to: **Alerting** → **Notification channels** (or **Alerting** → **Contact points** in newer versions)
4. Click **"New channel"** or **"Add contact point"**
5. Configure:
   - **Name:** `Slack - Forge Alerts`
   - **Type:** `Slack`
   - **Webhook URL:** Paste your Slack webhook URL
   - **Channel:** `#forge-alerts` (or `@username` for DMs)
   - **Title:** `{{ .GroupLabels.alertname }}`
   - **Text:** 
     ```
     {{ range .Alerts }}
     *Alert:* {{ .Annotations.summary }}
     *Description:* {{ .Annotations.description }}
     *Severity:* {{ .Labels.severity }}
     *Team:* {{ .Labels.team }}
     {{ end }}
     ```
6. Click **"Test"** to send test notification
7. Click **"Save"**

**Option B: Via Configuration File** (Recommended for production)

Create `monitoring/grafana/provisioning/notifiers/slack.yml`:

```yaml
notifiers:
  - name: slack-forge-alerts
    type: slack
    uid: slack-forge-alerts
    org_id: 1
    is_default: false
    settings:
      url: 'YOUR_SLACK_WEBHOOK_URL_HERE'
      channel: '#forge-alerts'
      title: '{{ .GroupLabels.alertname }}'
      text: |
        {{ range .Alerts }}
        *Alert:* {{ .Annotations.summary }}
        *Description:* {{ .Annotations.description }}
        *Severity:* {{ .Labels.severity }}
        *Team:* {{ .Labels.team }}
        *Duration:* {{ .Duration }}
        [View in Grafana]({{ .GeneratorURL }})
        {{ end }}
      username: 'Forge Alerts'
      icon_emoji: ':warning:'
```

**Restart Grafana:**
```bash
cd monitoring
docker-compose restart grafana
```

#### **3. Link Alert Rules to Slack Channel**

**Via Grafana UI:**

1. Go to: **Alerting** → **Alert rules**
2. Click on an alert rule (e.g., "High Error Rate")
3. Scroll to **"Notification"** section
4. Click **"Add contact point"** or **"Add notification channel"**
5. Select: `Slack - Forge Alerts`
6. Click **"Save"**

**Repeat for all alert rules you want to notify on.**

#### **4. Test Alert**

1. In Grafana, go to: **Alerting** → **Alert rules**
2. Find "High Error Rate" alert
3. Click **"..."** → **"Test rule"**
4. Check Slack channel - you should see test notification!

### **Example Slack Notification**

```
🚨 High Error Rate

*Alert:* Agent error rate is above 5%
*Description:* Error rate is 7.5% (threshold: 5%)
*Severity:* critical
*Team:* backend
*Duration:* 5m

[View in Grafana](http://localhost:3030/alerting/...)
```

### **Advanced: Multiple Slack Channels**

Route alerts by severity:

**Create multiple notification channels:**
- `Slack - Critical` → `#ops-critical` (for critical alerts)
- `Slack - Warnings` → `#forge-alerts` (for warnings)
- `Slack - Info` → `#forge-info` (for info alerts)

**Link to alert rules:**
- Critical alerts → `Slack - Critical`
- Warning alerts → `Slack - Warnings`
- Info alerts → `Slack - Info`

---

## 📞 **PagerDuty Integration**

### **Benefits**
- ✅ On-call management and rotation
- ✅ Escalation policies (auto-escalate if unacknowledged)
- ✅ Mobile app notifications (SMS, phone calls)
- ✅ Incident tracking and post-mortems
- ✅ Integration with calendars
- ✅ Better for critical production alerts

### **Setup Steps**

#### **1. Create PagerDuty Service**

1. Go to: https://app.pagerduty.com
2. Login or create account
3. Go to: **Configuration** → **Services**
4. Click **"New Service"**
5. Configure:
   - **Service Name:** `Forge Production`
   - **Description:** `Forge AI Agent Platform`
   - **Escalation Policy:** Create new or select existing
   - **Incident Urgency:** `High`
6. Click **"Add Integration"**
7. Select: **"Events API v2"**
8. **Copy the Integration Key** (looks like: `abc123def456...`)

#### **2. Create Escalation Policy** (Recommended)

1. Go to: **Configuration** → **Escalation Policies**
2. Click **"New Escalation Policy"**
3. Name: `Forge Critical Alerts`
4. Add escalation levels:
   - **Level 1:** On-call engineer (immediate)
   - **Level 2:** Backup engineer (after 5 minutes)
   - **Level 3:** Engineering manager (after 15 minutes)
5. Click **"Save"**
6. Assign to your PagerDuty service

#### **3. Configure Grafana Notification Channel**

**Option A: Via Grafana UI**

1. Open Grafana: http://localhost:3030
2. Go to: **Alerting** → **Notification channels**
3. Click **"New channel"**
4. Configure:
   - **Name:** `PagerDuty - Critical`
   - **Type:** `PagerDuty`
   - **Integration Key:** Paste your PagerDuty integration key
   - **Severity:** Map Grafana severities:
     - `critical` → `critical`
     - `warning` → `warning`
     - `info` → `info`
5. Click **"Test"** to create test incident
6. Click **"Save"**

**Option B: Via Configuration File**

Create `monitoring/grafana/provisioning/notifiers/pagerduty.yml`:

```yaml
notifiers:
  - name: pagerduty-critical
    type: pagerduty
    uid: pagerduty-critical
    org_id: 1
    is_default: false
    settings:
      integrationKey: 'YOUR_PAGERDUTY_INTEGRATION_KEY_HERE'
      severity: '{{ .CommonLabels.severity }}'
      description: '{{ .GroupLabels.alertname }}: {{ .CommonAnnotations.summary }}'
      details: |
        {
          "description": "{{ .CommonAnnotations.description }}",
          "team": "{{ .CommonLabels.team }}",
          "duration": "{{ .CommonLabels.duration }}",
          "grafana_url": "{{ .ExternalURL }}"
        }
```

**Restart Grafana:**
```bash
cd monitoring
docker-compose restart grafana
```

#### **4. Link Critical Alerts to PagerDuty**

**Via Grafana UI:**

1. Go to: **Alerting** → **Alert rules**
2. For **critical alerts** (Service Down, High Error Rate, Database Errors):
   - Click on alert rule
   - Add notification channel: `PagerDuty - Critical`
   - Save

**Recommended routing:**
- **Critical alerts** → PagerDuty (wake up on-call)
- **Warning alerts** → Slack (team awareness)
- **Info alerts** → Slack (optional)

#### **5. Test PagerDuty Integration**

1. In Grafana, go to: **Alerting** → **Alert rules**
2. Find "Service Down" alert
3. Click **"..."** → **"Test rule"**
4. Check PagerDuty - incident should be created!
5. Check your phone - you should get notification (if configured)

### **Example PagerDuty Incident**

**Incident Details:**
- **Title:** High Error Rate
- **Description:** Agent error rate is above 5%
- **Severity:** Critical
- **Source:** Forge Production
- **Custom Details:**
  - Error rate: 7.5%
  - Threshold: 5%
  - Team: backend
  - Duration: 5 minutes

**On-call engineer receives:**
- SMS notification
- Phone call (if not acknowledged)
- Mobile app push notification
- Email notification

---

## 🎛️ **Alert Routing Strategy**

### **Recommended Setup**

```
Critical Alerts (Service Down, High Error Rate, DB Errors)
  ↓
  ├─→ PagerDuty (wake up on-call engineer)
  └─→ Slack #ops-critical (team awareness)

Warning Alerts (Slow Response, High Retry Rate)
  ↓
  └─→ Slack #forge-alerts (team notification)

Info Alerts (Cost Spike, Quota Exceeded)
  ↓
  └─→ Slack #forge-info (optional, low priority)
```

### **Implementation**

1. **Create notification channels:**
   - `PagerDuty - Critical`
   - `Slack - Critical` → `#ops-critical`
   - `Slack - Warnings` → `#forge-alerts`
   - `Slack - Info` → `#forge-info`

2. **Link alert rules:**
   - **Critical alerts** → Both PagerDuty + Slack Critical
   - **Warning alerts** → Slack Warnings only
   - **Info alerts** → Slack Info only

3. **Configure PagerDuty escalation:**
   - Level 1: Primary on-call (immediate)
   - Level 2: Backup on-call (5 min)
   - Level 3: Engineering manager (15 min)

---

## 🔧 **Alternative: Direct Webhook Integration**

Your codebase already has `forge/core/alerting.py` with `AlertClient` that supports direct webhooks.

### **For Application-Level Alerts**

If you want to send alerts directly from Forge code (not via Grafana):

```python
from forge.core.alerting import get_alert_client

# Get alert client
alert_client = get_alert_client()

# Send alert
await alert_client.send_alert(
    policy_name="High Error Rate",
    metric="error_rate",
    value=7.5,
    threshold=5.0,
    message="Error rate exceeded threshold"
)
```

### **Environment Variables**

```bash
# Enable alerting
ALERTING_ENABLED=true

# Slack webhook
ALERTING_ENDPOINT=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
ALERTING_API_KEY=  # Not needed for Slack

# PagerDuty webhook
ALERTING_ENDPOINT=https://events.pagerduty.com/v2/enqueue
ALERTING_API_KEY=YOUR_PAGERDUTY_INTEGRATION_KEY
```

---

## 📊 **Monitoring Integration Status**

### **Current State**
- ✅ **Alert Rules:** 6 groups, 15+ rules configured
- ✅ **Alert Client Code:** `forge/core/alerting.py` with Slack/PagerDuty support
- ⚠️ **Notification Channels:** Not configured yet
- ⚠️ **Alert Routing:** Not set up yet

### **After Setup**
- ✅ **Alert Rules:** 6 groups, 15+ rules configured
- ✅ **Notification Channels:** Slack + PagerDuty configured
- ✅ **Alert Routing:** Critical → PagerDuty, Warnings → Slack
- ✅ **On-Call Management:** PagerDuty escalation policies
- ✅ **Team Collaboration:** Slack channel notifications

---

## 🧪 **Testing**

### **Test Slack Integration**

1. **Via Grafana UI:**
   - Alerting → Alert rules → Select rule → Test rule
   - Check Slack channel

2. **Via API:**
   ```bash
   curl -X POST http://localhost:3030/api/alerting/notifications/test \
     -H "Content-Type: application/json" \
     -d '{
       "name": "Slack - Forge Alerts",
       "type": "slack",
       "settings": {
         "url": "YOUR_WEBHOOK_URL"
       }
     }'
   ```

### **Test PagerDuty Integration**

1. **Via Grafana UI:**
   - Alerting → Alert rules → Select critical rule → Test rule
   - Check PagerDuty incidents page
   - Check phone notifications

2. **Via PagerDuty Test:**
   - PagerDuty → Services → Your Service → Test
   - Should create test incident

---

## 🚨 **Troubleshooting**

### **Slack Notifications Not Working**

1. **Check webhook URL:**
   ```bash
   curl -X POST YOUR_SLACK_WEBHOOK_URL \
     -H "Content-Type: application/json" \
     -d '{"text":"Test message"}'
   ```

2. **Check Grafana logs:**
   ```bash
   docker logs forge-grafana | grep -i slack
   ```

3. **Verify channel name:**
   - Use `#channel-name` (with #)
   - Channel must exist in Slack

### **PagerDuty Notifications Not Working**

1. **Check integration key:**
   - Verify key is correct
   - Check service is active

2. **Check Grafana logs:**
   ```bash
   docker logs forge-grafana | grep -i pagerduty
   ```

3. **Verify severity mapping:**
   - Grafana severity must match PagerDuty severity
   - Check alert rule labels

### **Alerts Not Firing**

1. **Check alert rule status:**
   - Grafana → Alerting → Alert rules
   - Verify rule is enabled
   - Check evaluation status

2. **Check Prometheus metrics:**
   - Verify metrics are being collected
   - Check query in Prometheus UI

3. **Check alert conditions:**
   - Verify threshold values
   - Check "for" duration

---

## 📚 **Resources**

- **Grafana Alerting Docs:** https://grafana.com/docs/grafana/latest/alerting/
- **Slack Incoming Webhooks:** https://api.slack.com/messaging/webhooks
- **PagerDuty Events API:** https://developer.pagerduty.com/docs/events-api-v2/overview/
- **Alert Rules Reference:** `monitoring/grafana/provisioning/alerting/rules.yml`

---

## ✅ **Checklist**

### **Slack Setup**
- [ ] Create Slack app and webhook
- [ ] Configure Grafana notification channel
- [ ] Link alert rules to Slack channel
- [ ] Test notification
- [ ] Set up multiple channels (critical, warnings, info)

### **PagerDuty Setup**
- [ ] Create PagerDuty account
- [ ] Create service and integration
- [ ] Set up escalation policy
- [ ] Configure Grafana notification channel
- [ ] Link critical alerts to PagerDuty
- [ ] Test incident creation
- [ ] Configure on-call schedule

### **Routing**
- [ ] Define alert routing strategy
- [ ] Configure multiple notification channels
- [ ] Link alerts to appropriate channels
- [ ] Test routing for each severity level

---

**Ready to set up alerting integrations! 🚀**

When you're ready to implement, follow this guide step-by-step. The setup takes about 30-45 minutes total.

