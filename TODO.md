# TODO List

## Features
- Implement Vector Arrow pointing towards Victim
  - Add visual indicator to help with navigation
  - Make arrow visible from drone camera view

## Optimizations
  - Separate config batch number from saving operations and batch creation system
  - Decouple these processes to improve responsiveness

## Automation
- When drone is within safe zone:
  - Automatically clear Environment (stop dataset capture)
  - Create new Environment (start dataset capture)
  - Implement detection of "safe zone" boundaries

## Bug Fixes
- Update config UI to reflect real values when changed
  - Fix synchronization between UI and actual config values
  - Ensure visual feedback when settings are modified

## Consistency Improvements
- Fix multiple creation issue: ensure only 1 Victim and only 1 Floor
  - Implement check to prevent duplicate objects
  - Clean up existing instances before creating new ones