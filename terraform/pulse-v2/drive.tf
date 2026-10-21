# Google Drive folder embeds: Pulse lists Drive folders shared with this service
# account. Its key is the GDRIVE_SA_EMAIL / GDRIVE_SA_PRIVATE_KEY Worker secrets.
#
# Created by the v1 stack (vm-hb-pulse) and adopted here when that stack was
# torn down. The key itself stays unmanaged: it was made by v1 and its private
# half only exists in the Worker secrets. To rotate, create a new key in the
# Google Cloud console, `wrangler secret put` both values, then delete the old key.

resource "google_project_service" "drive" {
  service            = "drive.googleapis.com"
  disable_on_destroy = false
}

resource "google_service_account" "pulse_drive" {
  account_id   = "pulse-drive-browser"
  display_name = "Pulse Drive Folder Browser"
  description  = "Used by Pulse to list Google Drive folders shared with this service account."

  depends_on = [google_project_service.drive]
}

# Adopt the existing resources. Safe to delete these blocks after the first apply.
import {
  to = google_project_service.drive
  id = "${var.google_project_id}/drive.googleapis.com"
}

import {
  to = google_service_account.pulse_drive
  id = "projects/${var.google_project_id}/serviceAccounts/pulse-drive-browser@${var.google_project_id}.iam.gserviceaccount.com"
}
