==================================
How to run an interactive debugger
==================================

The code can be debugged using an interactive tool such as ipdb [1]. The environment is already setup
to accept stdin interactions.

If you are running Docker using the command line, all you have to do is install the ipdb package in your container::

    docker-compose exec web pip3 install ipdb

See the documentation[1] for more information on how to use it.

.. [1] https://pypi.org/project/ipdb/
