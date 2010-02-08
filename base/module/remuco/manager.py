# =============================================================================
#
#    Remuco - A remote control system for media players.
#    Copyright (C) 2006-2010 by the Remuco team, see AUTHORS.
#
#    This file is part of Remuco.
#
#    Remuco is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Remuco is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Remuco.  If not, see <http://www.gnu.org/licenses/>.
#
# =============================================================================

import signal

import gobject

from remuco import log

_ml = None

def _sighandler(signum, frame):
    """Used by Manager. """
    
    log.info("received signal %i" % signum)
    if _ml is not None:
        _ml.quit()

def _init_main_loop():
    """Used by Manager. """
    
    global _ml
    
    if _ml is None:
        _ml = gobject.MainLoop()
        signal.signal(signal.SIGINT, _sighandler)
        signal.signal(signal.SIGTERM, _sighandler)
        gobject.ctrlc_add()
    
    return _ml

def _start_pa(pa):
    """Start the given player adapter with error handling."""
    
    log.info("start player adapter")
    try:
        pa.start()
    except StandardError, e:
        log.error("failed to start player adapter (%s)" % e)
        return False
    except Exception, e:
        log.exception("** BUG ** %s", e)
        return False
    else:
        log.info("player adapter started")
        return True

def _stop_pa(pa):
    """Stop the given player adapter with error handling."""
    
    log.info("stop player adapter")
    try:
        pa.stop()
    except Exception, e:
        log.exception("** BUG ** %s", e)
    else:
        log.info("player adapter stopped")

class _CustomObserver():
    """Helper class used by Manager.
    
    A custom observer uses a custom function to periodically check if a media
    player is running and automatically starts and stops the player adapter
    accordingly.
    
    """
    def __init__(self, pa, run_check_fn):
        """Create a new custom observer.
        
        @param pa:
            the PlayerAdapter to automatically start and stop
        @param run_check_fn:
            the function to call periodically to check if the player is running
            
        """
        self.__pa = pa
        self.__run_check_fn = run_check_fn
        self.__sid = gobject.idle_add(self.__check_first)
        
    def __check_first(self):
        
        self.__check()
        self.__sid = gobject.timeout_add(5123, self.__check)
        return False
        
    def __check(self):
        
        running = self.__run_check_fn()
        if running and self.__pa.stopped:
            _start_pa(self.__pa)
        elif not running and not self.__pa.stopped:
            _stop_pa(self.__pa)
        else:
            # nothing to do
            pass
        
        return True
        
    def disconnect(self):
        
        gobject.source_remove(self.__sid)


class Manager(object):
    """ Manages life cycle of a player adapter.
    
    A Manager cares about calling a PlayerAdapter's start and stop methods.
    Additionally, because Remuco needs a GLib main loop to run, it sets up and
    manages such a loop.
    
    It is intended for player adapters running stand-alone, outside the players
    they adapt. A Manager is not needed for player adapters realized as a
    plugin for a media player. In that case the player's plugin interface
    should care about the life cycle of a player adapter (see the Rhythmbox
    player adapter as an example).
    
    To activate a manager call run().
    
    """
    
    def __init__(self, pa, player_dbus_name=None, run_check_fn=None):
        """Create a new Manager.
        
        @param pa:
            the PlayerAdapter to manage
        @keyword player_dbus_name:
            if the player adapter uses DBus to communicate with its player set
            this to the player's well known bus name (see run() for more
            information)
        @keyword run_check_fn:
            optional function to call to check if the player is running, used
            for automatically starting and stopping the player
        
        When neither `player_dbus_name` nor `run_check_fn` is given, the
        adapter is started immediately, assuming the player is running and
        the adapter is ready to work.
        
        """
        self.__pa = pa
        self.__pa.manager = self
        
        self.__stopped = False
        
        self.__ml = _init_main_loop()

        self.__observer = None
        
        if player_dbus_name:
            log.info("start dbus observer")
            self.__observer = _DBusObserver(pa, player_dbus_name)
            log.info("dbus observer started")
        elif run_check_fn:
            log.info("start custom observer")
            self.__observer = _CustomObserver(pa, run_check_fn)
            log.info("custom observer started")
        else:
            # nothing to do
            pass
        
    def run(self):
        """Activate the manager.
        
        This method starts the player adapter, runs a main loop (GLib) and
        blocks until SIGINT or SIGTERM arrives or until stop() gets called. If
        this happens the player adapter gets stopped and this method returns.
        
        @note: If the keyword 'player_dbus_name' has been set in __init__(),
            then the player adapter does not get started until an application
            owns the bus name given by 'player_dbus_name'. It automatically
            gets started whenever the DBus name has an owner (which means the
            adapter's player is running) and it gets stopped when it has no
            owner. Obvisously here the player adapter may get started and
            stopped repeatedly while this method is running.
        
        """
        if self.__observer is None: # start pa directly
            ready = _start_pa(self.__pa)
        else: # observer will start pa
            ready = True
            
        if ready and not self.__stopped: # not stopped since creation 
            
            log.info("start main loop")
            try:
                self.__ml.run()
            except Exception, e:
                log.exception("** BUG ** %s", e)
            log.info("main loop stopped")
            
        if self.__observer is not None: # disconnect observer
            log.info("stop observer")
            self.__observer.disconnect()
            log.info("observer stopped")
        
        # stop pa
        _stop_pa(self.__pa)
        
    def stop(self):
        """Manually shut down the manager.
        
        Stops the manager's main loop and player adapter. As a result a
        previous call to run() will return now.
        """
        
        log.info("stop manager manually")
        self.__stopped = True
        self.__ml.quit()

class DummyManager(object):
    """Dummy manager which can be stopped - does nothing.
    
    A DummyManager is used for adapters which not yet or not at all have a
    Manager to ensure it is always safe to call PlayerAdapter.manager.stop().
    
    """
    
    def stop(self):
        """Stop me, I do nothing."""
