======================
How to style web pages
======================

This project handles front-end build step using Django Compressor.
Explicit build happens within Docker image build
using ``python manage.py compress`` command.

.. seealso:: :rfp:req:`1`

When DEBUG is True, online mode is also enabled, so post-processing takes place
at request time (if changes were detected).

Make sure to include any new JS
(and CSS, but you should not need that—see below)
within ``{% compress %}`` tag
(see existing templates for examples).


Editing JS
==========

Write modern JS. Babel should take care of converting it
to more conservative syntax that works in mainstream browsers.

Working with Tailwind
=====================

This project uses Tailwind for styling. It follows the “utility classes”
model, which has its own drawbacks but is probably the next best thing
after JSX and Web components (which, unfortunately, are tricky to have
if one wants to have server-side rendered HTML without switching
from Python to Node).

To change styling, read Tailwind reference
and apply relevant utility classes (e.g., ``p-4`` to set padding to 4
according to Tailwind’s measurements).

Some common utilities are also implemented in ``main.css``,
but it’s not recommended to make changes there because it’s more difficult
to know where they may have unexpected effect. Be sure to grep around
and understand how it works first.

It is also not recommended to spread styling across new CSS files.
Try to maintain the convention within this project instead.

.. important::

   Never construct Tailwind class strings dynamically.

   Tailwind needs to “see” the entire class, such as ``bg-rose-600``,
   appear in your code.
   If you write ``bg-{{ classes.warning }}-600`` in a template
   or ``text-${classes.warning}-100`` in JS,
   the build won’t include relevant style rules.

Not seeing your changes
-----------------------

At build step, Tailwind’s plugin needs to read all files
that reference any of its class names, in order to deliver a small
CSS containing only the required rules. This means that
if you change styling by adding a new Tailwind class
(e.g., changing padding from ``p-2`` to ``p-3``),
Tailwind needs to build CSS again.

This works fine if you made changes to ``main.css`` directly.

But, unfortunately, our build is not able to deduce that
it also needs to regenerate CSS
whenever you edited e.g. a template file to add a new CSS class to an element
(so that Tailwind adds corresponding new style rules).

To force it to do so, after you edit classes in a template (or JS, etc.),
you can ``touch static/css/main.css`` to update its mtime, and subsequent
request should have regenerated CSS.


Styling error pages
===================

There’s a gotcha with error pages, in that if you run
with DEBUG (see :doc:`/howto/develop-locally`)
you won’t get “production-style” error pages (Django shows its own),
and without DEBUG you will have to rebuild the image every time
to see your error page styling take effect.

Running with DEBUG and then changing DEBUG to False in settings.py
in running container will result in missing styling.

One workaround is to do that, but *also* temporarily
change ``STATICFILES_STORAGE`` setting, e.g.::

    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

(Don’t commit that change, though.)
