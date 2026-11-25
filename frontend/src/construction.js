import { RECORDS } from './records'

export const JOB_DOCTYPE = 'Sidra Construction Job'
export const jobTone = (status) => RECORDS.jobs.status[status] || 'muted'
export const stageTone = (status) => ({ Planned: 'pending', 'In Progress': 'current', Completed: 'completed' })[status] || 'muted'
