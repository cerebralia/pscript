"""
The event module provides a system for properties and events,
to let different components of an application react to each-other and
to user input.

In short:

* The :class:`Component <flexx.event.Component>` class provides a base class
  which can be subclassed to create the different components of an app.
* Each component has :class:`properties <flexx.event.Property>` to reflect
  the state of the component.
* Properties can only be mutated by :class:`actions <flexx.event.action>`.
  Calling (i.e. invoking) an action will not apply the action at once; actions
  are processed in batches.
* When properties are modified (i.e. the state is changed),
  corresponding :class:`reactions <flexx.event.reaction>`
  will be invoked. The reactions are processed when all pending actions
  are done. This means that during processing reactions, the state never changes,
  which is a great thing to rely on!
* Reactions can also react to events generated by :func:`emitters <flexx.event.emitter>`,
  such as mouse events.
* The :class:`event loop <flexx.event.Loop>` object is responsible for scheduling
  actions and reactions and can be used by the user to e.g. make a function be
  called later. It intergrates with Python's own asyncio loop.

The asynchronous nature of actions combined with the fact that the state does
not change during processing reactions, makes it easy to reason about
cause and effect. The information flows in one direction. This concept was
gratefully taken from modern frameworks such as React/Flux and Veux. 

.. image:: https://docs.google.com/drawings/d/e/2PACX-1vSHp4iha6CTgjsQ52x77gn0hqQP4lZD-bcaVeCfRKhyMVtaLeuX5wpbgUGaIE0Sce_kBT9mqrfEgQxB/pub?w=503

One might suggest that the information flow is still circular, because there
is an arrow going from reactions to actions. This is true, but note that
actions invoked from reactions are not directly executed; they are pended and
will be executed only after all reactions are done.


Relation to other parts of Flexx
--------------------------------

This event system and its :class:`Component <flexx.event.Component>` class
form the basis for :class:`app.PyComponent <flexx.app.PyComponent>`,
:class:`app.JsComponent <flexx.app.JsComponent>` and the UI system
in ``flexx.ui``. It can be used in both Python and JavaScript and works exactly
the same in both languages.

Other than that, this is a generic event system that could drive any system
that is based on asyncio.

Event object
------------

An event is something that has occurred at a certain moment in time,
such as the mouse being pressed down or a property changing its value.
In Flexx, events are represented with dictionary objects that
provide information about the event (such as what button was pressed,
or the old and new value of a property). A custom :class:`Dict <flexx.event.Dict>`
class is used that inherits from ``dict`` but allows attribute access,
e.g. ``ev.button`` as an alternative to ``ev['button']``.

Each event object has at least two attributes: ``source``,
a reference to the Component object emitting the event, and ``type``, a string
indicating the type of the event.


The Component class
-------------------

The :class:`Component <flexx.event.Component>` class provides a base
class for objects that have properties, actions, reactions and emitters.
E.g. ``flexx.ui.Widget`` inherits from ``flexx.app.JsComponent``,
which inherits from ``flexx.event.Component``.


.. code-block:: python

    class MyObject(event.Component):
        ...  # attributes/properties/actions/reactions/emitters go here


Properties represent state
--------------------------

:class:`Properties <flexx.event.Property>` can be defined using one of
the several property classes. For example:

.. code-block:: python

    class MyObject(event.Component):
       
        foo = event.AnyProp(8, settable=True, doc='can have any value')
        bar = event.IntProp()

Properties accept one positional arguments to set the default value. If not
given, a sensible default value is used that depends on the type of property.
The ``foo`` property above is marked as settable, so that the class will have
a ``set_foo()`` action. Docs can be added too. Note that properties
are readonly: they can can only be mutated by actions.

Property values can be initialized when a component is created (also
non-settable properties):

.. code-block:: python

    c = MyComponent(foo=42)

One can also set the initial value of a property to a function object.
This creates an "implicit reaction" that sets the property, and makes it possible
to hook things up in a very concise manner. In the example below, the label
text will be automatically updated when the username property changes:

.. code-block:: python

    c = UiLabel(text=lambda: self.username)

An event is emitted every time that a property changes. This event has attributes
``old_value`` and ``new_value`` (except for in-place array mutations, as
explained below). At initialization, a component sends out an event for each property,
which has the same value for ``old_value`` and ``new_value``.

Component classes can also have :class:`Attributes <flexx.event.Attribute>`,
which are read-only (usually static) non-observable values (e.g. ``JsComponent.id``).


Actions can mutate properties
-----------------------------

:class:`Actions <flexx.event.action>` can be defined to mutate properties:

.. code-block:: python

    class MyObject(event.Component):
       
        foo = event.AnyProp(8, settable=True, doc='can have any value')
        bar = event.IntProp()
        
        @event.action
        def increase_bar(self):
            self._mutate_bar(self.bar + 1)
            # shorthand for self._mutate('bar', self.bar + 1)

Actions can have any number of (positional) arguments. Note that actions are
asynchronous, i.e. calling an action will not apply it immediately, unless it is
called from another action.

Mutations are done via the :func:`_mutate <flexx.event.Component._mutate>` method,
or by the auto-generated ``_mutate_xx()`` methods.
Mutations can only be done from an action. Trying
to do so otherwise will result in an error. This may seem limiting at first,
but it greatly helps keeping it easy to reason about information flowing
through your application, even as it scales.


Mutations to array-like properties
----------------------------------

The above shows the simple and most common use of mutations. For list
properties, mutations can also be done in-place:

.. code-block:: python

    class MyObject(event.Component):
       
        items = event.ListProp()
        
        def add_item(self, item):
            self._mutate_items([item], 'insert', len(self.items))

This allows more fine-grained control over state updates, which can also
be handled by reactions in much more efficient ways. The types of mutations are
'set' (the default), 'insert', 'replace', and 'remove'. In the latter, the
provided value is the number of elements to remove. For the others it must
be a list of elements to set/insert/replace at the specified index.


Emitters create events
----------------------

:func:`Emitters <flexx.event.emitter>` make it easy to generate events.
Similar to actions, they are created with a decorator.

.. code-block:: python

    class MyObject(event.Component):
    
        @event.emitter
        def mouse_down(self, js_event):
            ''' Event emitted when the mouse is pressed down.
            '''
            return dict(button=js_event.button)

Emitters can have any number of arguments and should return a dictionary,
which will get emitted as an event, with the event type matching the name
of the emitter.

Note that stricly speaking emitters are not necessary as ``Component.emit()``
can be used to generate an event. However, they provide a mechanism to 
generate an event based on certain input data, and also document the
events that a component may emit.


Reactions
---------

:func:`Reactions <flexx.event.reaction>` are used to react to events and
changes in properties, using an underlying handler function:


.. code-block:: python

    class MyObject(event.Component):
       
        first_name = event.StringProp(settable=True)
        last_name = event.StringProp(settable=True)
        
        @event.reaction('first_name', 'last_name')
        def greet(self, *events):
            print('hi', self.first_name, self.last_name)
        
        @event.reaction('!foo')
        def handle_foo(self, *events):
            for ev in events:
                print(ev)


This example demonstrates multiple concepts. Firstly, the reactions are
connected via *connection-strings* that specify the types of the
event; in this case the ``greeter`` reaction is connected to "first_name" and
"last_name", and ``handle_foo`` is connected to the event-type "foo" of the
object. This connection-string can also be a path, e.g.
"sub.subsub.event_type". This allows for some powerful mechanics, as
discussed in the section on dynamism.

One can also see that the reaction-function accepts ``*events`` argument.
This is because reactions can be passed zero or more events. If a reaction
is called manually (e.g. ``ob.handle_foo()``) it will have zero events.
When called by the event system, it will have at least 1 event. When
e.g. a property is set twice, the function will be called
just once, but with multiple events. If all events need to be processed
individually, use ``for ev in events: ...``.

In most cases, you will connect to events that are known beforehand,
like those corresponding to properties and emitters. 
If you connect to an event that is not known (like "foo" in the example
above) Flexx will display a warning. Use ``'!foo'`` as a connection string
(i.e. prepend an exclamation mark) to suppress such warnings.

Another useful feature of the event system is that a reaction can connect to
multiple events at once, as the ``greet`` reaction does.

The following is less common, but it is possinle to create a reaction from a
normal function, by using the
:func:`Component.reacion() <flexx.event.Component.reaction>` method:

.. code-block:: python

    c = MyComponent()
    
    # Using a decorator
    @c.reaction('foo', 'bar')
    def handle_func1(self, *events):
        print(events)
    
    # Explicit notation
    def handle_func2(self, *events):
        print(events)
    c.reaction(handle_func2, 'foo', 'bar')
    # this is fine too: c.reaction('foo', 'bar', handle_func2)


Implicit reactions
==================

One can also create reactions without specifying connection strings. Flexx
will then figure out what properties are being accessed and will call the
reaction whenever one of these change. We refer to such reactions as "implicit
reactions". This is a convenient feature, but
should probably be avoided when a lot (say hundreds) of properties are accessed.

.. code-block:: python

    class MyObject(event.Component):
       
        first_name = event.StringProp(settable=True)
        last_name = event.StringProp(settable=True)
        
        @event.reaction
        def greet(self):
            print('hi', self.first_name, self.last_name)

A similar useful feature is to assign a property (at initialization) using a
function. In such a case, the function is turned into an implicit reaction.
This can be convenient to easily connect different parts of an app.

.. code-block:: python

    class MyObject(event.Component):
       
        first_name = event.StringProp(settable=True)
        last_name = event.StringProp(settable=True)
    
    person = MyObject()
    label = UiLabel(text=lambda: person.first_name)


Reacting to in-place mutations
==============================

In-place mutations to lists or arrays can be reacted to by processing
the events one by one:

.. code-block:: python
    
    class MyComponent(event.Component):
    
        @event.reaction('other.items')
        def track_array(self, *events):
            for ev in events:
                if ev.mutation == 'set':
                    self.items[:] = ev.objects
                elif ev.mutation == 'insert':
                    self.items[ev.index:ev.index] = ev.objects
                elif ev.mutation == 'remove':
                    self.items[ev.index:ev.index+ev.objects] = []  # objects is int here
                elif ev.mutation == 'replace':
                    self.items[ev.index:ev.index+len(ev.objects)] = ev.objects
                else:
                    assert False, 'we cover all mutations'

For convenience, the mutation can also be "replicated" using the
``flexx.event.mutate_array()`` and ``flexx.event.mutate_dict()`` functions.


Connection string syntax
========================

The strings used to connect events follow a few simple syntax rules:

* Connection strings consist of parts separated by dots, thus forming a path.
  If an element on the path is a property, the connection will automatically
  reset when that property changes (a.k.a. dynamism, more on this below).
* Each part can end with one star ('*'), indicating that the part is a list
  and that a connection should be made for each item in the list. 
* With two stars, the connection is made *recursively*, e.g. "children**"
  connects to "children" and the children's children, etc.
* Stripped of '*', each part must be a valid identifier (ASCII).
* The total string optionally has a label suffix separated by a colon. The
  label itself may consist of any characters.
* The string can have a "!" at the very start to suppress warnings for
  connections to event types that Flexx is not aware of at initialization
  time (i.e. not corresponding to a property or emitter).

An extreme example could be ``"!foo.children**.text:mylabel"``, which connects
to the "text" event of the children (and their children, and their children's
children etc.) of the ``foo`` attribute. The "!" is common in cases like
this to suppress warnings if not all children have a ``text`` event/property.

Labels
======

Labels are a feature that makes it possible to infuence the order by
which reactions are called, and provide a means to disconnect
specific (groups of) handlers. 

.. code-block:: python
    
    class MyObject(event.Component):
    
        @event.reaction('foo')
        def given_foo_handler(*events):
                ...
        
        @event.reaction('foo:aa')
        def my_foo_handler(*events):
            # This one is called first: 'aa' < 'given_f...'
            ...

When an event is emitted, any connected reactions are scheduled in the
order of a key, which is the label if present, and
otherwise the name of the name of the reaction.

The label can also be used in the
:func:`disconnect() <flexx.event.Component.disconnect>` method:

.. code-block:: python

    @h.reaction('foo:mylabel')
    def handle_foo(*events):
        ...
    
    ...
    
    h.disconnect('foo:mylabel')  # don't need reference to handle_foo


Dynamism
========

Dynamism is a concept that allows one to connect to events for which
the source can change. For the following example, assume that ``Node``
is a ``Component`` subclass that has properties ``parent`` and
``children``.

.. code-block:: python
    
    main = Node()
    main.parent = Node()
    main.children = Node(), Node()
    
    @main.reaction('parent.foo')
    def parent_foo_handler(*events):
        ...
    
    @main.reaction('children*.foo')
    def children_foo_handler(*events):
        ...

The ``parent_foo_handler`` gets invoked when the "foo" event gets
emitted on the parent of main. Similarly, the ``children_foo_handler``
gets invoked when any of the children emits its "foo" event. Note that
in some cases you might also want to connect to changes of the ``parent``
or ``children`` property itself.

The event system automatically reconnects reactions when necessary. This
concept makes it very easy to connect to the right events without the
need for a lot of boilerplate code.

Note that the above example would also work if ``parent`` would be a
regular attribute instead of a property, but the reaction would not be
automatically reconnected when it changed.


Implicit dynamism
=================

Implicit reactions are also dynamic, maybe even more so! In the example below,
the reaction accesses the ``children`` property, thus it will be called whenever
that property changes. It also connects to the ``visible`` event of
all children, and to the ``foo`` event of all children that are visible.

.. code-block:: python
    
   @main.reaction
    def _implicit_reacion():
        for child in main.children:
            if child.visible:
                do_something_with(child.foo)

This mechanism is powerful, but one can see how it can potentially
access (and thus connect to) many properties, especially if the reaction
calls other functions that access more properties. Also keep in mind that
implicit reactions have more overhead (because they fully reconnect
every time after they are called). One should probably avoid them for
properties that change 100 times per second.


Patterns
--------

The event system presented here is quite flexible and designed to cover the needs
of a variety of event/messaging mechanisms. This section discusses
how this system relates to some common patterns, and how these can be
implemented.

Observer pattern
================

The idea of the observer pattern is that observers keep track (the state
of) of an object, and that an object is agnostic about what it's tracked by.
For example, in a music player, instead of writing code to update the
window-title inside the function that starts a song, there would be a
concept of a "current song", and the window would listen for changes to
the current song to update the title when it changes.

In ``flexx.event``, a ``Component`` object keeps track of its observers
(reactions) and notifies them when there are changes. In our music player
example, there would be a property "current_song", and a reaction to
take action when it changes.

As is common in the observer pattern, the reactions keep track of the
objects that they observe. Therefore both ``Reaction`` and ``Component``
objects have a ``dispose()`` method for cleaning up.

Signals and slots
=================

The Qt GUI toolkit makes use of a mechanism called "signals and slots" as
an easy way to connect different components of an application. In
``flexx.event`` signals translate to properties and assoctated setter actions,
and slots to the reactions that connect to them.

Although signals and slots provide a convenient mechanism, they make it easy
to create "spaghetti apps" where the information flows all over the place,
which is exactly what frameworks like Flux, Veux and Flexx try to overcome.

Overloadable event handlers
===========================

In Qt, the "event system" consists of methods that handles an event, which
can be overloaded in subclasses to handle an event differently. In
``flexx.event``, actions and reactions can similarly be re-implemented in
subclasses, and these can call the original handler using ``super()`` if needed.

Publish-subscribe pattern
==========================

In pub-sub, publishers generate messages identified by a 'topic', and
subscribers can subscribe to such topics. There can be zero or more publishers
and zero or more subscribers to any topic. 

In ``flexx.event`` a `Component` object can play the role of a broker.
Publishers can simply emit events. The event type represents the message
topic. Subscribers are represented by handlers.

"""

import logging
logger = logging.getLogger(__name__)
del logging

import sys
assert sys.version_info > (3, 5), "Flexx.event needs Python 3.5+"
del sys

# flake8: noqa
from ._dict import Dict
from ._loop import Loop, loop
from ._action import Action, action
from ._reaction import Reaction, reaction
from ._emitter import emitter, Emitter
from ._attribute import Attribute
from ._property import *
from ._component import Component, mutate_array, mutate_dict
