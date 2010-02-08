/*   
 *   Remuco - A remote control system for media players.
 *   Copyright (C) 2006-2010 by the Remuco team, see AUTHORS.
 *
 *   This file is part of Remuco.
 *
 *   Remuco is free software: you can redistribute it and/or modify
 *   it under the terms of the GNU General Public License as published by
 *   the Free Software Foundation, either version 3 of the License, or
 *   (at your option) any later version.
 *
 *   Remuco is distributed in the hope that it will be useful,
 *   but WITHOUT ANY WARRANTY; without even the implied warranty of
 *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *   GNU General Public License for more details.
 *
 *   You should have received a copy of the GNU General Public License
 *   along with Remuco.  If not, see <http://www.gnu.org/licenses/>.
 *   
 */
package remuco.client.common.util;

import remuco.client.common.UserException;

/**
 * A very stupid logging framework.
 * <p>
 * This logging class does not distinguish between different log levels. The
 * reason is that on JavaME devices everything should be as simple as possible
 * and having a sophisticated level-based log handler just might slow down
 * performance on older devices.
 * <p>
 * By default logging goes to {@link System#out}. To direct logging to anohter
 * location, assign a {@link ILogPrinter} using {@link #setOut(ILogPrinter)}.
 */
public final class Log {

	private static ILogPrinter out = new ConsoleLogger();

	/**
	 * Log a bug.
	 * 
	 * @param id
	 *            some unique identifier as a hint where in the source the bug
	 *            has occurred
	 */
	public static void bug(String id) {
		ln("[BUG] " + id);
	}

	/**
	 * Log a bug related to an exception.
	 * 
	 * @param id
	 *            some unique identifier as a hint where in the source the bug
	 *            has occurred
	 * @param ex
	 *            the exception related to the bug
	 */
	public static void bug(String id, Exception ex) {

		ln("[BUG] " + id, ex);

	}

	/**
	 * Log a debug message.
	 * <p>
	 * This is exactly the same as {@link #ln(String)} but using this method
	 * it's easier to find debug output in the source and to comment or delete
	 * it when it is not needed anymore.
	 * 
	 * @param msg
	 */
	public static void debug(String msg) {
		out.println(msg);
	}

	/**
	 * Log a message.
	 * 
	 * @param msg
	 *            the log message
	 */
	public static void ln(String msg) {
		out.println(msg);
	}

	/**
	 * Log an Exception. Output will be in the format 's ( e.getMessage)'
	 * 
	 * @param s
	 * @param e
	 */
	public static void ln(String s, Throwable e) {
		out.println(s + " (" + e.getMessage() + ")");
	}

	/**
	 * Log a {@link UserException}.
	 * 
	 * @param s
	 *            a prefix for the log
	 * @param e
	 *            the exception
	 * 
	 */
	public static void ln(String s, UserException e) {
		out.println(s + e.getError() + " (" + e.getDetails() + ")");
	}

	/**
	 * Set the log sink.
	 * 
	 * @param out
	 *            the out sink to use for log messages
	 */
	public static void setOut(ILogPrinter out) {
		if (out == null)
			throw new NullPointerException("null logger not supported");
		Log.out = out;
	}

}
