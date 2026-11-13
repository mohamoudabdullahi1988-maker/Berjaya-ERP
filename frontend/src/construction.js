export const JOB_DOCTYPE = 'Sidra Construction Job'

const TONE = {
  Enquiry: 'muted',
  Quoted: 'muted',
  Contracted: 'current',
  'In Progress': 'current',
  'On Hold': 'pending',
  Completed: 'completed',
  'Defects Period': 'completed',
  Closed: 'completed',
  Cancelled: 'blocked',
}
export const jobTone = (status) => TONE[status] || 'muted'
export const stageTone = (status) => ({ Planned: 'pending', 'In Progress': 'current', Completed: 'completed' })[status] || 'muted'
