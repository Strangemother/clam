"""
WebSocket Sound Server for SunVox

A WebSocket server that receives JSON events and plays sounds using the SunVox library.

Example events:
    {"action": "note", "note": "C4"}
    {"action": "note", "note": 49, "velocity": 100}
    {"action": "note_off"}
    {"action": "play_file", "file": "assets/test.sunvox"}
    {"action": "stop"}
    {"action": "volume", "value": 0.8}
    {"action": "beep", "note": "C4", "duration": 0.3}

Usage:
    python ws_sound_server.py [--host 0.0.0.0] [--port 8765]

Then connect via WebSocket and send JSON events.
"""

import asyncio
import json
import time
import argparse
from pathlib import Path

try:
    import websockets
except ImportError:
    print("Installing websockets...")
    import subprocess
    subprocess.check_call(['pip', 'install', 'websockets'])
    import websockets

from modules import Generator, Module
from notes import Notes
from player import player_factory, Player


class SoundEventHandler:
    """Handles sound events from WebSocket messages."""
    
    def __init__(self):
        self.player = None
        self.module = None
        self.notes = Notes()
        self._running = False
        
        # Map device/event names to sounds
        self.event_sound_map = {
            # Example mappings - customize these for your network events
            'door_open': ('beep', {'note': 'C4', 'duration': 0.2}),
            'door_close': ('beep', {'note': 'E4', 'duration': 0.2}),
            'motion_detected': ('beep', {'note': 'G4', 'duration': 0.1}),
            'light_on': ('beep', {'note': 'C5', 'duration': 0.15}),
            'light_off': ('beep', {'note': 'A3', 'duration': 0.15}),
            'button_press': ('beep', {'note': 'F4', 'duration': 0.1}),
            'alarm': ('play_file', {'file': 'assets/test.sunvox'}),
        }
    
    def init(self):
        """Initialize the sound system."""
        if self._running:
            return True
            
        print("Initializing SunVox sound system...")
        self.player = player_factory.spawn_player()
        
        if self.player is None:
            print("ERROR: Failed to create player")
            return False
            
        # Create a generator module for playing notes
        self.module = Generator()
        self.player.add_module(self.module, connect_to=self.player.OUTPUT)
        
        self._running = True
        print("Sound system initialized!")
        return True
    
    def shutdown(self):
        """Shutdown the sound system."""
        if self.player and self._running:
            print("Shutting down sound system...")
            self.player.stop()
            self.player.close()
            self._running = False
    
    def parse_note(self, note_value):
        """Parse a note value - can be string like 'C4' or integer."""
        if isinstance(note_value, str):
            # Try to get from Notes class
            note = getattr(self.notes, note_value, None)
            if note is None:
                # Try parsing as octave_note format
                try:
                    letter = note_value[0].upper()
                    octave = int(note_value[1:])
                    note_map = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}
                    note = self.notes.octave_note(octave, note_map.get(letter, 0))
                except (IndexError, ValueError):
                    note = self.notes.C4  # Default
            return note
        return int(note_value)
    
    async def handle_event(self, event_data: dict) -> dict:
        """
        Handle a sound event.
        
        Args:
            event_data: Dictionary with event parameters
            
        Returns:
            Response dictionary with status
        """
        if not self._running:
            return {'status': 'error', 'message': 'Sound system not initialized'}
        
        action = event_data.get('action', '').lower()
        
        try:
            if action == 'note':
                return await self._handle_note(event_data)
            elif action == 'note_off':
                return await self._handle_note_off(event_data)
            elif action == 'beep':
                return await self._handle_beep(event_data)
            elif action == 'play_file':
                return await self._handle_play_file(event_data)
            elif action == 'stop':
                return await self._handle_stop(event_data)
            elif action == 'volume':
                return await self._handle_volume(event_data)
            elif action == 'device_event':
                return await self._handle_device_event(event_data)
            elif action == 'map_event':
                return await self._handle_map_event(event_data)
            elif action == 'list_mappings':
                return {'status': 'ok', 'mappings': self.event_sound_map}
            elif action == 'ping':
                return {'status': 'ok', 'message': 'pong'}
            else:
                return {'status': 'error', 'message': f'Unknown action: {action}'}
                
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    async def _handle_note(self, data: dict) -> dict:
        """Play a note."""
        note = self.parse_note(data.get('note', 'C4'))
        velocity = data.get('velocity', 129)
        track = data.get('track', 0)
        
        self.module.sv_send_event(track, note, velocity)
        return {'status': 'ok', 'action': 'note', 'note': note}
    
    async def _handle_note_off(self, data: dict) -> dict:
        """Stop the current note."""
        track = data.get('track', 0)
        self.module.sv_send_event(track, self.notes.NOTE_OFF)
        return {'status': 'ok', 'action': 'note_off'}
    
    async def _handle_beep(self, data: dict) -> dict:
        """Play a note for a duration then stop."""
        note = self.parse_note(data.get('note', 'C4'))
        duration = data.get('duration', 0.3)
        velocity = data.get('velocity', 129)
        track = data.get('track', 0)
        
        self.module.sv_send_event(track, note, velocity)
        await asyncio.sleep(duration)
        self.module.sv_send_event(track, self.notes.NOTE_OFF)
        
        return {'status': 'ok', 'action': 'beep', 'note': note, 'duration': duration}
    
    async def _handle_play_file(self, data: dict) -> dict:
        """Play a SunVox file."""
        filename = data.get('file', 'assets/test.sunvox')
        
        if not Path(filename).exists():
            return {'status': 'error', 'message': f'File not found: {filename}'}
        
        self.player.play_file(filename)
        return {'status': 'ok', 'action': 'play_file', 'file': filename}
    
    async def _handle_stop(self, data: dict) -> dict:
        """Stop playback."""
        self.player.stop()
        return {'status': 'ok', 'action': 'stop'}
    
    async def _handle_volume(self, data: dict) -> dict:
        """Set volume (0.0 to 1.0)."""
        value = float(data.get('value', 1.0))
        value = max(0.0, min(1.0, value))
        self.player.volume(value)
        return {'status': 'ok', 'action': 'volume', 'value': value}
    
    async def _handle_device_event(self, data: dict) -> dict:
        """
        Handle a device event from your network.
        Maps device events to sounds based on event_sound_map.
        
        Example:
            {"action": "device_event", "event": "door_open", "device": "front_door"}
        """
        event_name = data.get('event', '')
        device = data.get('device', 'unknown')
        
        if event_name in self.event_sound_map:
            sound_action, sound_params = self.event_sound_map[event_name]
            sound_event = {'action': sound_action, **sound_params}
            result = await self.handle_event(sound_event)
            result['device'] = device
            result['original_event'] = event_name
            return result
        
        return {
            'status': 'ok', 
            'message': f'No sound mapped for event: {event_name}',
            'device': device
        }
    
    async def _handle_map_event(self, data: dict) -> dict:
        """
        Add or update a device event to sound mapping.
        
        Example:
            {"action": "map_event", "event": "custom_event", 
             "sound_action": "beep", "sound_params": {"note": "D4", "duration": 0.2}}
        """
        event_name = data.get('event')
        sound_action = data.get('sound_action', 'beep')
        sound_params = data.get('sound_params', {'note': 'C4', 'duration': 0.2})
        
        if not event_name:
            return {'status': 'error', 'message': 'Event name required'}
        
        self.event_sound_map[event_name] = (sound_action, sound_params)
        return {
            'status': 'ok', 
            'action': 'map_event',
            'event': event_name,
            'mapped_to': (sound_action, sound_params)
        }


class WebSocketSoundServer:
    """WebSocket server for receiving sound events."""
    
    def __init__(self, host='0.0.0.0', port=8765):
        self.host = host
        self.port = port
        self.handler = SoundEventHandler()
        self.clients = set()
    
    async def handle_client(self, websocket):
        """Handle a WebSocket client connection."""
        client_addr = websocket.remote_address
        print(f"Client connected: {client_addr}")
        self.clients.add(websocket)
        
        try:
            async for message in websocket:
                try:
                    event_data = json.loads(message)
                    print(f"Received: {event_data}")
                    
                    response = await self.handler.handle_event(event_data)
                    await websocket.send(json.dumps(response))
                    
                except json.JSONDecodeError:
                    error_response = {'status': 'error', 'message': 'Invalid JSON'}
                    await websocket.send(json.dumps(error_response))
                    
        except websockets.exceptions.ConnectionClosed:
            print(f"Client disconnected: {client_addr}")
        finally:
            self.clients.discard(websocket)
    
    async def broadcast(self, message: dict):
        """Broadcast a message to all connected clients."""
        if self.clients:
            msg = json.dumps(message)
            await asyncio.gather(*[client.send(msg) for client in self.clients])
    
    async def start(self):
        """Start the WebSocket server."""
        if not self.handler.init():
            print("Failed to initialize sound system!")
            return
        
        print(f"Starting WebSocket Sound Server on ws://{self.host}:{self.port}")
        print("\nAvailable actions:")
        print('  {"action": "note", "note": "C4"}')
        print('  {"action": "note", "note": 49, "velocity": 100}')
        print('  {"action": "note_off"}')
        print('  {"action": "beep", "note": "C4", "duration": 0.3}')
        print('  {"action": "play_file", "file": "assets/test.sunvox"}')
        print('  {"action": "stop"}')
        print('  {"action": "volume", "value": 0.8}')
        print('  {"action": "device_event", "event": "door_open", "device": "front"}')
        print('  {"action": "map_event", "event": "my_event", "sound_action": "beep", "sound_params": {"note": "D4"}}')
        print('  {"action": "list_mappings"}')
        print('  {"action": "ping"}')
        print("\nWaiting for connections...")
        
        try:
            async with websockets.serve(self.handle_client, self.host, self.port):
                await asyncio.Future()  # Run forever
        except KeyboardInterrupt:
            print("\nShutting down...")
        finally:
            self.handler.shutdown()


def main():
    parser = argparse.ArgumentParser(description='WebSocket Sound Server for SunVox')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=8765, help='Port to listen on (default: 8765)')
    args = parser.parse_args()
    
    server = WebSocketSoundServer(host=args.host, port=args.port)
    asyncio.run(server.start())


if __name__ == '__main__':
    main()
