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
package remuco.client.jme.ui.screenies;

import javax.microedition.lcdui.Graphics;
import javax.microedition.lcdui.Image;

import remuco.client.common.data.PlayerInfo;
import remuco.client.jme.ui.Theme;

/**
 * A generic screeny to display images. Images get displayed centered. If an
 * image to display is bigger than the screeny's area, it gets scaled down.
 */
public final class ImageScreeny extends Screeny {

	public ImageScreeny(PlayerInfo player) {
		super(player);
	}

	protected void initRepresentation() throws ScreenyException {

		setImage(Image.createImage(width, height));

		// fill with background color

		g.setColor(theme.getColor(Theme.RTC_BG));
		g.fillRect(0, 0, width, height);

	}

	protected void updateRepresentation() {

		Image img = (Image) data;

		g.setColor(theme.getColor(Theme.RTC_BG));
		g.fillRect(0, 0, width, height);

		if (img == null)
			return;

		img = Theme.shrinkImageIfNeeded(img, width, height);

		g.drawImage(img, width / 2, height / 2, Graphics.HCENTER
				| Graphics.VCENTER);

	}

}
