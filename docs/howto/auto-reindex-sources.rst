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

  This method uses ``celerybeat`` scheduler. It’s easier to set up,
  but puts more importance on monitoring the status of task worker.

  .. seealso:: :data:`bibxml.settings.AUTO_REINDEX_INTERVAL`

How frequently to reindex?
--------------------------

In short: it’s recommended to check how frequently the sources change
and how long it takes to index the largest source,
and pick a value higher than the maximum between those two.

Long answer: you may want to ensure that reindex interval
is larger than the time it takes for a source to be reindexed
(which could be multiple minutes for sources with many documents,
such as Internet Drafts)—otherwise, task queue may grow indefinitely.

Furthermore, it’s currently recommended to not reindex too often,
as it’d overwhelm task outcome listings in management GUI
(making it harder to track down issues) and cause unnecessary requests
to Git server APIs.

Other than that, it’s OK to reindex sources as often as you want.

.. note::

   If no changes were detected in source’s underlying Git repo
   (the HEAD commit is the same), then indexing task will skip reindexing.

   This ensures the service does not reindex unnecessarily,
   but it also means that if you change indexing implementation
   you’d need to ensure each source
   has at least one commit since then for changes to have effect.

.. note:: Regardless of the method you choose, make sure to monitor
          task execution as part of overall
          :doc:`service monitoring in production </topics/production-setup>`.
