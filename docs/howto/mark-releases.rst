========================
How to mark new releases
========================

To mark a new release, tag current commit with new version.

This repository uses the following versioning scheme::

    yyyy.m.d_i

Where ``i`` starts with 1
and increments with each release made this day.

Example tagging command::

    git tag -s "2022.1.29_1" -m "Tag today’s release"
