====================================
How to reindex sources automatically
====================================

Service’s database serves as more of a cache,
and all data is indexed from Git repositories
(termed :term:`indexable sources <indexable source>`).
Thus, to ensure up-to-date information output in API and GUI,
you may want to reindex those sources periodically.

There are two possible approaches to this:

- Set up an integration that periodically invokes service’s
  reindex API endpoint.

  This method is more explicit, and allows you to catch
  an error returned by reindex API endpoint if service experiences issues.

- Set ``AUTO_REINDEX_INTERVAL`` to a positive integer
  in production environment.

  This method is easier to set up.

  .. note:: Set this value to a high enough number of seconds.
            This helps avoid overwhelming management GUI
            with no-op task outcomes.

  .. seealso:: :data:`bibxml.settings.AUTO_REINDEX_INTERVAL`

How frequently to reindex?
--------------------------

Generally, you can reindex sources as often as you want.
If no changes were detected in source’s underlying Git repo
(the HEAD commit is the same), then indexing task will not do the work
of actually reading every file.

However, it’s currently recommended to not reindex too often,
as that will overwhelm task outcome listings in management GUI
(making it harder to track down issues) and cause unnecessary requests
to Git server APIs.

It’s recommended to confirm how frequently the sources usually change,
and pick a value somewhat higher than that—regardless of whether
you implement scheduled API endpoint calls
or use the ``AUTO_REINDEX_INTERVAL`` setting.

.. note:: Regardless of the method you choose, make sure to monitor
          task execution as part of overall
          :doc:`service monitoring in production </topics/production-setup>`.
