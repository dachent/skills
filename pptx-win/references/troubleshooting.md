# Troubleshooting

## Common local Windows issues

### PowerPoint launches a modal dialog and automation hangs

Likely causes:
- Protected View
- file repair prompt
- read-only or sync conflict prompt
- add-in startup dialog

Mitigation:
- work on local copies, not email attachments or remote temp files
- copy cloud-synced files to a normal local work directory before editing
- close any existing interactive PowerPoint windows using the same file
- rerun the smoke test to confirm clean automation

### File is locked or output cannot be saved

Likely causes:
- the file is already open in PowerPoint
- OneDrive or SharePoint sync lock
- antivirus or backup tool touching the file

Mitigation:
- save to a new output filename
- close the source deck everywhere else
- the bundled scripts now stage editable deck outputs under `%TEMP%\\pptx-win` before copying them to the requested destination
- if a synced-folder destination still fails, rerun with a plain local destination to isolate whether the final filesystem copy is blocked

### Fonts differ from expectation

COM rendering uses local installed fonts. If a brand font is missing, the deck can reflow.

Mitigation:
- inspect exported PNGs after saving
- if the font is unavailable, note the substitution clearly
- prefer the user's installed Office fonts when possible

### COM cleanup fails and PowerPoint stays running

Mitigation:
- always close the presentation before quitting the app
- release COM objects in `finally`
- force garbage collection after `Quit()`

### Hidden slides are missed during review

Mitigation:
- use `presentation_report.ps1` and check the `hidden` field
- do not rely on image export alone to identify hidden slides
