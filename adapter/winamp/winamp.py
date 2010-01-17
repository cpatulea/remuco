#    Copyright (C) 2009 Yaron Inger, http://ingeration.blogspot.com
#    Copyright (C) 2010 Catalin Patulea <cat@vv.carleton.ca>
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#    or download it from http://www.gnu.org/licenses/gpl.txt

#    Revision History:
#
#    11/05/2008 Version 0.1
#    	- Initial release
#
#    31/12/2009 Version 0.2
#    	- Added support for keyword queries (queryAsKeyword)
#
#    16/01/2010 Version 0.3
#     - Cleaned up structure definitions
#     - Free memory allocated in Winamp process
#     - Better detection of Winamp windows and error handling
#     - More functions for controlling Winamp (seek, getExtendedFileInfo, ...)

from ctypes import *
from ctypes import wintypes
import win32api, win32con, win32gui, win32process, pywintypes, winerror
import os
import random
import time

class Error(Exception):
	pass

class WinampNotFoundError(Error):
	def __str__(self):
		return "Winamp main window not found. Is Winamp started?"

class WinampError(Error):
	pass

# Winamp main window IPC
WM_WA_IPC = win32con.WM_USER
# Winamp's media library IPC
WM_ML_IPC = WM_WA_IPC + 0x1000

# add item to playlist
IPC_ENQUEUEFILE = 100
# playback status
IPC_ISPLAYING = 104
# delete winamp's internal playlist
IPC_DELETE = 101
# get output time
IPC_GETOUTPUTTIME = 105
IPC_JUMPTOTIME = 106
# sets playlist position
IPC_SETPLAYLISTPOS = 121
# sets volume
IPC_SETVOLUME = 122
# gets list length
IPC_GETLISTLENGTH = 124
IPC_GETLISTPOS = 125
IPC_GETINFO = 126
# gets given index playlist file
IPC_GETPLAYLISTFILE = 211
# gets given index playlist title
IPC_GETPLAYLISTTITLE = 212
IPC_GET_SHUFFLE = 250
IPC_GET_REPEAT = 251
IPC_SET_SHUFFLE = 252
IPC_SET_REPEAT = 253
# gets handle to auxiliary windows (see IPC_GETWND_*)
IPC_GETWND = 260
IPC_GET_EXTENDED_FILE_INFO = 290
# next playlist track
IPC_GET_NEXT_PLITEM = 361
IPC_IS_FULLSCREEN = 630
IPC_SETRATING = 639
IPC_GETRATING = 640
# current playing title
IPC_GET_PLAYING_TITLE = 3034

IPC_REGISTER_WINAMP_IPCMESSAGE = 65536

IPC_PE_DELETEINDEX = 104

# runs an ml query
ML_IPC_DB_RUNQUERY = 0x0700
# runs an ml query as a string
ML_IPC_DB_RUNQUERY_SEARCH = 0x0701
# frees ml query results from winamp's memory
ML_IPC_DB_FREEQUERYRESULTS = 0x0705

IPC_GETWND_EQ = 0
IPC_GETWND_PE = 1
IPC_GETWND_MB = 2
IPC_GETWND_VIDEO = 3

IPC_VIDCMD = 1002

INFO_SAMPLERATE = 0
INFO_BITRATE = 1
INFO_CHANNELS = 2
INFO_VIDEO = 3
INFO_VIDEO_DESCRIPTION = 3
INFO_SAMPLERATE_HZ = 4

VIDCMD_FULLSCREEN = 0

# playback possible options
PLAYBACK_NOT_PLAYING = 0
PLAYBACK_PLAYING = 1
PLAYBACK_PAUSE = 3

GET_TRACK_POSITION = 0
GET_TRACK_LENGTH = 1

# winamp buttons commands
BUTTON_COMMAND_PREVIOUS = 40044
BUTTON_COMMAND_PLAY = 40045
BUTTON_COMMAND_PAUSE = 40046
BUTTON_COMMAND_STOP = 40047
BUTTON_COMMAND_NEXT = 40048

# sort playlist by path and filename
ID_PE_S_PATH = 40211

ML_IPC_TREEITEM_GETCHILD = 0x121
ML_IPC_TREEITEM_GETNEXT = 0x122
ML_IPC_TREEITEM_GETINFO = 0x124
ML_IPC_TREEITEM_GETROOT = 0x129
MLTI_TEXT = 1

"""
typedef struct tagCOPYDATASTRUCT {
	ULONG_PTR dwData;
	DWORD cbData;
	PVOID lpData;
} COPYDATASTRUCT, *PCOPYDATASTRUCT;

dwData
	Specifies data to be passed to the receiving application. 
cbData
	Specifies the size, in bytes, of the data pointed to by the lpData member. 
lpData
	Pointer to data to be passed to the receiving application. This member can be NULL.
"""
class COPYDATASTRUCT(Structure):
	_fields_ = [("dwData", c_ulong),
				("cbData", c_ulong),
				("lpData", c_void_p)]

"""
typedef struct 
{
  itemRecord *Items;
  int Size;
  int Alloc;
} itemRecordList;
"""
class itemRecordList(Structure):
	_fields_ = [("Items", c_void_p),
				("Size", c_int),
				("Alloc", c_int)]

"""
typedef struct
{
  char *filename;
  char *title;
  char *album;
  char *artist;
  char *comment;
  char *genre;
  int year;
  int track;
  int length;
  char **extended_info;
  // currently defined extended columns (while they are stored internally as integers
  // they are passed using extended_info as strings):
  // use getRecordExtendedItem and setRecordExtendedItem to get/set.
  // for your own internal use, you can set other things, but the following values
  // are what we use at the moment. Note that setting other things will be ignored
  // by ML_IPC_DB*.
  // 
  //"RATING" file rating. can be 1-5, or 0 or empty for undefined
  //"PLAYCOUNT" number of file plays.
  //"LASTPLAY" last time played, in standard time_t format
  //"LASTUPD" last time updated in library, in standard time_t format
  //"FILETIME" last known file time of file, in standard time_t format
  //"FILESIZE" last known file size, in kilobytes.
  //"BITRATE" file bitrate, in kbps
	//"TYPE" - "0" for audio, "1" for video

} itemRecord;
"""
class itemRecord(Structure):
	_fields_ = [("filename", c_char_p),
				("title", c_char_p),
				("album", c_char_p),
				("artist", c_char_p),
				("comment", c_char_p),
				("genre", c_char_p),
				("year", c_int),
				("track", c_int),
				("length", c_int),
				("extended_info", c_char_p)]

"""
typedef struct 
{
  char *query;
  int max_results;      // can be 0 for unlimited
  itemRecordList results;
} mlQueryStruct;
"""
class mlQueryStruct(Structure):
	_fields_ = [("query", c_char_p),
				("max_results", c_int),
				("itemRecordList", itemRecordList)]

"""
typedef struct {
  int cmd;
  int x;
  int y;
  int align;
} windowCommand; // send this as param to an IPC_PLCMD, IPC_MBCMD, IPC_VIDCMD
"""
class windowCommand(Structure):
	_fields_ = [("cmd", c_int),
				("x", c_int),
				("y", c_int),
				("align", c_int)]

"""
typedef struct {
  const char *filename;
  const char *metadata;
  char *ret;
  size_t retlen;
} extendedFileInfoStruct;
"""
class extendedFileInfoStruct(Structure):
	_fields_ = [("filename", c_char_p),
				("metadata", c_char_p),
				("ret", c_char_p),
				("retlen", c_size_t)]

"""
typedef struct {
  size_t	size;			// size of this struct
  UINT_PTR	id;				// depends on contxext
  UINT_PTR	parentId;		// 0 = root, or ML_TREEVIEW_ID_*
  char		*title;			// pointer to the buffer contained item name. 
  size_t	titleLen;		// used for GetInfo 
  BOOL		hasChildren;	// TRUE - has children
  int		imageIndex;		// index of the associated image
} MLTREEITEM;

typedef struct {
  MLTREEITEM	item;	// item data
  UINT			mask;	// one or more of MLTI_* flags
  UINT_PTR		handle; // Handle to the item. If handle is NULL item->id will be used
} MLTREEITEMINFO;
"""
UINT_PTR = c_uint # FIXME?

class MLTREEITEM(Structure):
	_fields_ = [("size", c_size_t),
				("id", UINT_PTR),
				("parentId", UINT_PTR),
				("title", c_char_p),
				("titleLen", c_size_t),
				("hasChildren", wintypes.BOOL),
				("imageIndex", c_int)]

class MLTREEITEMINFO(Structure):
	_fields_ = [("item", MLTREEITEM),
				("mask", c_uint),
				("handle", UINT_PTR)]

class Winamp(object):
	def __init__(self):
		# get main Winamp window handle
		try:
			self.__mainWindowHWND = win32gui.FindWindow("Winamp v1.x", None)
		except win32gui.error, e:
			if e[0] == winerror.ERROR_FILE_NOT_FOUND:
				raise WinampNotFoundError()
			else: # some other unexpected error
				raise
		
		# do this early because part of our initialization uses
		# __copyDataToWinamp
		_, pid = win32process.GetWindowThreadProcessId(self.__mainWindowHWND)

		# open Winamp's process
		self.__hProcess = windll.kernel32.OpenProcess(
			win32con.PROCESS_VM_OPERATION | win32con.PROCESS_VM_READ | win32con.PROCESS_VM_WRITE,
			False, pid)

		# use documented IPC call to get Playlist Editor window
		self.__playlistHWND = self.__sendUserMessage(IPC_GETWND_PE, IPC_GETWND)
		
		# unofficial way of getting Media Library window (undocumented but
		# unlikely to change), see:
		# http://forums.winamp.com/showthread.php?threadid=173940
		ipcMessageAddr = self.__copyDataToWinamp("LibraryGetWnd")
		self.IPC_LibraryGetWnd = self.__sendUserMessage(ipcMessageAddr,
			IPC_REGISTER_WINAMP_IPCMESSAGE)
		self.__freeDataInWinamp(ipcMessageAddr)
		
		self.__mediaLibraryHWND = self.__sendUserMessage(0,
			self.IPC_LibraryGetWnd)

	def detach(self):
		"""Detaches from Winamp's process."""
		windll.kernel32.CloseHandle(self.__hProcess)

	def __readStringFromMemory(self, address, isUnicode = False):
		"""Reads a string from Winamp's memory address space."""

		if isUnicode:
			bufferLength = win32con.MAX_PATH * 2
			buffer = create_unicode_buffer(bufferLength * 2)
		else:
			bufferLength = win32con.MAX_PATH
			buffer = create_string_buffer(bufferLength)

		bytesRead = c_ulong(0)

		"""Note: this is quite an ugly hack, because we assume the string will have a maximum
		size of MAX_PATH (=260) and that we're not in an end of a page.
		
		A proper way to solve it would be:
			1. calling VirutalQuery.
			2. Reading one byte at a time. (?)
			3. Use CreateRemoteThread to run strlen on Winamp's process.
		"""
		windll.kernel32.ReadProcessMemory(self.__hProcess, address, buffer, bufferLength, byref(bytesRead))

		return buffer.value
	
	def enqueueFile(self, filePath):
		"""Enqueues a file in Winamp's playlist.

		filePath is the given file path to enqueue.
		"""

		# prepare copydata structure for sending data
		cpyData = create_string_buffer(filePath)
		cds = COPYDATASTRUCT(c_ulong(IPC_ENQUEUEFILE),
							 c_ulong(len(cpyData.raw)),
							 cast(cpyData, c_void_p))

		# send copydata message
		win32api.SendMessage(self.__mainWindowHWND,
							 win32con.WM_COPYDATA,
							 0,
							 addressof(cds))

	def query(self, queryString, queryType = ML_IPC_DB_RUNQUERY):
		"""Queries Winamp's media library and returns a list of items matching the query.
		
		The query should include filters like '?artist has \'alice\''.
		For more information, consult your local Winamp forums or media library.
		"""
		queryStringAddr = self.__copyDataToWinamp(queryString)

		# create query structs and copy to winamp
		recordList = itemRecordList(0, 0, 0)
		queryStruct = mlQueryStruct(cast(queryStringAddr, c_char_p), 0, recordList)
		queryStructAddr = self.__copyDataToWinamp(queryStruct)

		# run query
		win32api.SendMessage(self.__mediaLibraryHWND, WM_ML_IPC, queryStructAddr, queryType)
		
		self.__freeDataInWinamp(queryStringAddr)

		receivedQuery = self.__readDataFromWinamp(queryStructAddr, mlQueryStruct)

		items = []

		buf = create_string_buffer(sizeof(itemRecord) * receivedQuery.itemRecordList.Size)
		windll.kernel32.ReadProcessMemory(self.__hProcess, receivedQuery.itemRecordList.Items, buf, sizeof(buf), 0)

		for i in xrange(receivedQuery.itemRecordList.Size):
			item = self.__readDataFromWinamp(receivedQuery.itemRecordList.Items + (sizeof(itemRecord) * i), itemRecord)

			self.__fixRemoteStruct(item)

			items.append(item)

		# free results
		win32api.SendMessage(self.__mediaLibraryHWND, WM_ML_IPC, queryStructAddr, ML_IPC_DB_FREEQUERYRESULTS)

		return items
	
	def queryAsKeyword(self, queryString):
		"""Queries Winamp's media library and returns a list of items matching the query.
		
		The query should be a keyword, like 'alice' (then the query is then treated as a string query).
		This makes Winamp search the requested keyword in every data field in the media library database
		(such as Artist, Album, Track Name, ...).
		"""
		return self.query(queryString, ML_IPC_DB_RUNQUERY_SEARCH)
	
	def __copyDataToWinamp(self, data):
		if type(data) is str:
			dataToCopy = create_string_buffer(data)
		else:
			dataToCopy = data

		# allocate data in Winamp's address space
		lpAddress = windll.kernel32.VirtualAllocEx(self.__hProcess, None, sizeof(dataToCopy), win32con.MEM_COMMIT, win32con.PAGE_READWRITE)
		if not lpAddress:
			raise pywintypes.error(GetLastError(), "VirtualAllocEx")

		# write data to Winamp's memory
		rc = windll.kernel32.WriteProcessMemory(self.__hProcess, lpAddress, addressof(dataToCopy), sizeof(dataToCopy), None)
		if not rc:
			raise pywintypes.error(GetLastError(), "WriteProcessMemory")

		return lpAddress
	
	def __freeDataInWinamp(self, addr):
		rc = windll.kernel32.VirtualFreeEx(self.__hProcess, addr, 0, win32con.MEM_RELEASE)
		if not rc:
			raise pywintypes.error(GetLastError(), "VirtualFreeEx")

	def __readDataFromWinamp(self, address, ctypesType, stringLen=win32con.MAX_PATH):
		if ctypesType is c_char_p:
			buffer = create_string_buffer(stringLen)
		else:
			buffer = create_string_buffer(sizeof(ctypesType))

		bytesRead = c_ulong(0)
		if windll.kernel32.ReadProcessMemory(self.__hProcess, address, buffer, sizeof(buffer), byref(bytesRead)) == 0:
			# we're in a new page
			if address / 0x1000 != address + sizeof(buffer):
				# possible got into an unpaged memory region, read until end of page
				windll.kernel32.ReadProcessMemory(self.__hProcess, address, buffer, ((address + 0x1000) & 0xfffff000) - address, byref(bytesRead))
			else:
				raise RuntimeError("ReadProcessMemory failed at 0x%08x." % address)

		if ctypesType is c_char_p:
			return cast(buffer, c_char_p)
		else:
			return cast(buffer, POINTER(ctypesType))[0]
	
	def __fixRemoteStruct(self, structure):
		offset = 0

		for i in xrange(len(structure._fields_)):
			(field_name, field_type) = structure._fields_[i]

			if field_type is c_char_p or field_type is c_void_p:
				# get pointer address
				address = cast(addressof(structure) + offset, POINTER(c_int))[0]
				
				# ignore null pointers
				if address != 0x0:
					setattr(structure, field_name, self.__readDataFromWinamp(address, field_type))

			offset += sizeof(field_type)
	
	def __sendUserMessage(self, wParam, lParam, hwnd = None):
		"""Sends a user message to the given hwnd with the given wParam and lParam."""
		if hwnd is None:
			targetHWND = self.__mainWindowHWND
		else:
			targetHWND = hwnd

		return win32api.SendMessage(targetHWND, WM_WA_IPC, wParam, lParam)

	def __sendCommandMessage(self, wParam, lParam, hwnd = None):
		"""Sends a command message to the given hwnd with the given wParam and lParam."""
		if hwnd is None:
			targetHWND = self.__mainWindowHWND
		else:
			targetHWND = hwnd

		return win32api.SendMessage(targetHWND, win32con.WM_COMMAND, wParam, lParam)
	
	def getPlaybackStatus(self):
		"""Gets Winamp's playback status. Use the constants PLAYBACK_NOT_PLAYING, 
		PLAYBACK_PLAYING and PLAYBACK_PAUSE = 3 to resolve status."""
		return self.__sendUserMessage(0, IPC_ISPLAYING)
	
	def getPlayingTrackLength(self):
		"""Gets the length in seconds of the current playing track."""
		return self.__sendUserMessage(GET_TRACK_LENGTH, IPC_GETOUTPUTTIME)

	def getPlayingTrackPosition(self):
		"""Gets the position in milliseconds of the current playing track."""
		return self.__sendUserMessage(GET_TRACK_POSITION, IPC_GETOUTPUTTIME)
	
	def getExtendedFileInfo(self, filename, metadataField, retlen=4096):
		"""Gets extended info for a particular filename.
		
		metadataField can be:
			title
			artist
			albumartist
			album
			genre
			year
			disc
			publisher
			comment
			track
			composer
			conductor
		"""
		xfi = extendedFileInfoStruct()
		xfi.filename = filenameAddr = self.__copyDataToWinamp(filename)
		xfi.metadata = metadataAddr = self.__copyDataToWinamp(metadataField)
		xfi.ret = retAddr = self.__copyDataToWinamp("\x00" * retlen)
		xfi.retlen = retlen
		xfiAddr = self.__copyDataToWinamp(xfi)

		rc = self.__sendUserMessage(xfiAddr, IPC_GET_EXTENDED_FILE_INFO)
		ret = self.__readDataFromWinamp(retAddr, c_char_p, xfi.retlen)
		self.__freeDataInWinamp(retAddr)
		self.__freeDataInWinamp(metadataAddr)
		self.__freeDataInWinamp(filenameAddr)
		self.__freeDataInWinamp(xfiAddr)
		
		if rc == 1:
			return ret.value
		else:
			raise WinampError("Input plugin does not support getExtendedFileInfo")

	def getCurrentPlayingInfo(self, mode):
		"""Gets info about the current playing song (INFO_*)."""
		return self.__sendUserMessage(mode, IPC_GETINFO)

	def clearPlaylist(self):
		"""Clears the playlist."""
		return self.__sendUserMessage(0, IPC_DELETE)
	
	def getPlaylistPosition(self):
		"""Gets the playlist position."""
		return self.__sendUserMessage(0, IPC_GETLISTPOS)

	def setPlaylistPosition(self, position):
		"""Sets the playlist position in the given position number (zero based)."""
		return self.__sendUserMessage(position, IPC_SETPLAYLISTPOS)
	
	def getVolume(self):
		"""Gets the Winamp volume in range [0,255]."""
		return self.__sendUserMessage(-666, IPC_SETVOLUME)

	def setVolume(self, volume):
		"""Sets the internal Winamp's volume meter. Will only accept values in the range 0-255."""
		assert volume >= 0 and volume <= 255

		self.__sendUserMessage(volume, IPC_SETVOLUME)
	
	def getRepeat(self):
		"""Gets the state of the repeat button."""
		return bool(self.__sendUserMessage(0, IPC_GET_REPEAT))

	def setRepeat(self, repeat):
		"""Sets the state of the repeat button."""
		self.__sendUserMessage(int(repeat), IPC_SET_REPEAT)

	def getShuffle(self):
		"""Gets the state of the shuffle button."""
		return bool(self.__sendUserMessage(0, IPC_GET_SHUFFLE))

	def setShuffle(self, shuffle):
		"""Sets the state of the shuffle button."""
		self.__sendUserMessage(int(shuffle), IPC_SET_SHUFFLE)
	
	def getFullscreen(self):
		"""Gets the fullscreen state of the video or visualization."""
		return bool(self.__sendUserMessage(0, IPC_IS_FULLSCREEN))

	def toggleFullscreen(self):
		"""Toggles the fullscreen state of the video or visualization."""
		winCmd = windowCommand()
		winCmd.cmd = VIDCMD_FULLSCREEN
		winCmd.x, winCmd.y, winCmd.align = 0, 0, 0

		winCmdAddr = self.__copyDataToWinamp(winCmd)
		self.__sendUserMessage(winCmdAddr, IPC_VIDCMD)
		self.__freeDataInWinamp(winCmdAddr)

	def getCurrentPlayingTitle(self):
		"""Returns the title of the current playing track"""
		address = self.__sendUserMessage(0, IPC_GET_PLAYING_TITLE)

		return self.__readStringFromMemory(address, True)
	
	def getPlaylistFile(self, position):
		"""Returns the filename of the specified position in the playlist."""
		address = self.__sendUserMessage(position, IPC_GETPLAYLISTFILE)

		return self.__readStringFromMemory(address)

	def getPlaylistTitle(self, position):
		"""Returns the title of the specified position in the playlist."""
		address = self.__sendUserMessage(position, IPC_GETPLAYLISTTITLE)

		return self.__readStringFromMemory(address)

	def getRating(self):
		"""Gets the rating (0 no rating, 1-5 stars) for the current item."""
		return self.__sendUserMessage(0, IPC_GETRATING)

	def setRating(self, rating):
		"""Sets the rating (0 no rating, 1-5 stars) for the current item.
		
		Note: This is a no-op if the Media Library "Local Media" plugin
		(ml_local.dll) is not installed.
		"""
		self.__sendUserMessage(rating, IPC_SETRATING)
		
	def getListLength(self):
		"""Returns the length of the current playlist."""
		return self.__sendUserMessage(0, IPC_GETLISTLENGTH)
	
	def getPlaylistFilenames(self):
		"""Retrieves a list of the current playlist song filenames."""
		return [self.getPlaylistFile(position) for position in range(self.getListLength())]
	
	def setPlaylistFilenames(self, filenames):
		"""Replaces the current playlist with the given filenames."""
		self.clearPlaylist()
		for filename in filenames:
			self.enqueueFile(filename)

	playlist = property(getPlaylistFilenames, setPlaylistFilenames)

	def getPlaylistTitles(self):
		"""Retrieves a list of the current playlist song titles."""
		return [self.getPlaylistTitle(position) for position in range(self.getListLength())]

	def removePlaylistPosition(self, position):
		"""Removes the playlist item at the specified position."""
		self.__sendUserMessage(IPC_PE_DELETEINDEX, position, self.__playlistHWND)

	def getMediaLibraryChildren(self, path):
		"""Get Media Library items under the specified path.
		
		The path is given as a list of components, ex:
		  ["Local Media", "Never Played"]
		
		Returns a list of (title, handle) tuples.
		"""
		
		handle = win32api.SendMessage(self.__mediaLibraryHWND, WM_ML_IPC,
			0, ML_IPC_TREEITEM_GETROOT)
		
		while True:
			siblings = self.__getMediaLibrarySiblings(handle)
			
			if not path:
				return siblings

			siblings = dict(siblings)
			title = path.pop(0)
			handle = siblings[title]
			
			handle = win32api.SendMessage(self.__mediaLibraryHWND, WM_ML_IPC,
				handle, ML_IPC_TREEITEM_GETCHILD)

			if not handle: # can also be found from MLTREEITEM.hasChildren
				raise WinampError("Item %r has no children" % title)
		
	def __getMediaLibrarySiblings(self, firstHandle):
		items = []
		handle = firstHandle

		while handle:
			title = self.__getMediaLibraryTitleByHandle(handle)
			items.append((title, handle))
			
			handle = win32api.SendMessage(self.__mediaLibraryHWND, WM_ML_IPC,
				handle, ML_IPC_TREEITEM_GETNEXT)
		
		return items

	def __getMediaLibraryTitleByHandle(self, handle):
		info = MLTREEITEMINFO()
		info.handle = handle
		info.mask = MLTI_TEXT
		info.item.size = sizeof(info.item)
		info.item.titleLen = win32con.MAX_PATH - 1
		titleAddr = self.__copyDataToWinamp("\x00" * win32con.MAX_PATH)
		info.item.title = titleAddr
		
		infoAddr = self.__copyDataToWinamp(info)
		rc = win32api.SendMessage(self.__mediaLibraryHWND, WM_ML_IPC,
			infoAddr, ML_IPC_TREEITEM_GETINFO)
		if rc == 1:
			title = self.__readDataFromWinamp(titleAddr, c_char_p)

		self.__freeDataInWinamp(titleAddr)
		self.__freeDataInWinamp(infoAddr)
		
		if rc == 1:
			return title.value
		else:
			raise WinampError("ML_IPC_TREEITEM_GETINFO returned %d" % rc)

	def next(self):
		"""Sets playlist marker to next song."""
		self.__sendCommandMessage(BUTTON_COMMAND_NEXT, 0)
	
	def previous(self):
		"""Sets playlist marker to previous song."""
		self.__sendCommandMessage(BUTTON_COMMAND_PREVIOUS, 0)
	
	def pause(self):
		"""Pauses Winamp's playback."""
		self.__sendCommandMessage(BUTTON_COMMAND_PAUSE, 0)

	def play(self):
		"""Starts / resumes playing Winamp's playback, or restarts current playing song."""
		self.__sendCommandMessage(BUTTON_COMMAND_PLAY, 0)
	
	def stop(self):
		"""Stops Winamp's playback."""
		self.__sendCommandMessage(BUTTON_COMMAND_STOP, 0)
	
	def seek(self, position):
		"""Seeks to the specified position (milliseconds)."""
		rc = self.__sendUserMessage(position, IPC_JUMPTOTIME)
		if rc == -1:
			raise WinampError("Winamp not playing")
		elif rc < 0:
			raise WinampError("Unknown error %d" % rc)
		# elif rc == 1: # end of file

	def sortPlaylist(self):
		"""Sorts the current playlist alphabetically."""
		self.__sendCommandMessage(ID_PE_S_PATH, 0, self.__playlistHWND)
	
	def playAlbum(self, album):
		"""Plays a given album name."""
		self.playlist = self.query("album = \"%s\"" % album)
		self.stop()
		self.sortPlaylist()
		self.setPlaylistPosition(0)
		self.play()

def printMediaLibraryItem(item):
	print "Filename: %s\nTrack: %s, Album: %s, Artist: %s\nComment: %s, Genre: %s" % (item.filename, item.track, item.album, item.artist, item.comment, item.genre)

if __name__ == "__main__":
	# little demonstration...
	
	w = Winamp()

	print "Current playlist:"
	print w.getPlaylistTitles()

	items = w.query("artist has \"opeth\"")
	[printMediaLibraryItem(item) for item in items]

	w.playlist = w.query("artist has \"jane's\"")
	w.sortPlaylist()

	print w.playlist

	"Playing album..."
	w.playAlbum("Red")