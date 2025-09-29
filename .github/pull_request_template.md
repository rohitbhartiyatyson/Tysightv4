## Description
*Please include a summary of the changes and the related issue. Please also include relevant motivation and context.*

## Type of change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] This change requires a documentation update

---
- [ ] **Soft Reset performed:** Clear Streamlit cache and hard-refresh the browser. On the server run:

  streamlit cache clear
  tail -n 200 logs/streamlit_no_pythonpath.log

- [ ] **Debug Panel check:** Open the Streamlit Debug Panel and verify that agent logs show no ModuleNotFoundError and that the agent can be invoked locally.

### Handoff Documentation Checklist
*This checklist must be completed for all PRs that modify application logic or architecture.*

- [ ] **Documentation Check:** Have the relevant handoff "source" documents (, , ) been updated to reflect the changes in this PR?

---
## How Has This Been Tested?
*Please describe the tests that you ran to verify your changes. Provide instructions so we can reproduce.*

- [ ] Running smoke tests...
pytest -q
- [ ] Manual Test in Streamlit App
