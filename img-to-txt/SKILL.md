---
name: img-to-txt
description: >-
  Scan image and create file with exact content.
  USE WHEN: User sent image and ask to create file.
  NOT FOR: Image analyzing, design.
---

# Image to text

Algo:
1. User attach image.
2. You read.
3. You create all files with exact names with exact content.

Branches:
1. If user don't attached image ask for it and wait until attached.
3. If you can't see file name on image or there is name clash - stop, ask user where to store files.