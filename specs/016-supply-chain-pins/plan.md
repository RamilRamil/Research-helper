# Plan

Freeze from running/built `app` image: `pip freeze`.
Replace `requirements.txt` with exact `==` pins (full freeze that Docker
installs). Rebuild `app` once to verify.

No hashes. No CI.
