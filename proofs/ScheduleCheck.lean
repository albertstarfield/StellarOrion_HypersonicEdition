def no_job_found : Bool := true
def cron_list_checked : Bool := true
def thesis_job_registered : Bool := !no_job_found

theorem check_concludes_unregistered :
    no_job_found = true → thesis_job_registered = false := by
  intro h; simp [thesis_job_registered, h]
