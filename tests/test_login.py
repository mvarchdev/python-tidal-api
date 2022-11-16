from email.mime import image
import json

from random import sample
from tracemalloc import stop
import tidalapi

import socket
import sys
import os
import logging
import threading
import time


session = tidalapi.Session(tidalapi.Config(tidalapi.Quality.lossless))

# session.login_oauth_simple()
loginc, future = session.login_oauth()

print(loginc.expires_in, loginc.user_code,
      loginc.verification_uri, loginc.verification_uri_complete)


def picture_url(img_uuid, width=1280, height=1280):
    """
        A url to a picture

        :param width: pixel width, maximum 2000
        :type width: int
        :param height: pixel height, maximum 2000
        :type height: int

        Accepted sizes: 80x80, 160x160, 320x320, 640x640 and 1280x1280
        """
    uuid = img_uuid.replace('-', '/')
    return tidalapi.models.IMG_URL.format(uuid=uuid, width=width, height=height)


def afterlogin(future=None):
    # favtracks = session.user.favorites.tracks()

    # for track in favtracks:
    #     print("Track name:", track.name)
    #     print("Track id:", track.id)
    #     print("Track stream url:", session.get_track_url(track.id), "\n")

    searchtext = "stanko lobotka"

    serres = session.search("track", searchtext, 10)
    print("Found for searching \""+searchtext+"\":")

    # testtrack = tidalapi.Track()
    # testtrack.album = tidalapi.Album()
    # testtrack.album.image

    for track in serres.tracks:
        print("TRACKID:", track.id)
        print("TRACK NAME:", track.name)
        print("TRACK ARTIST:", track.artist.name)
        print("TRACK ALBUM:", track.album.name)
        print("IMG UUID:", track.album.img_uuid)
        print("IMG URL:", picture_url(track.album.img_uuid))
        print("\n")

    if(len(serres.tracks) == 0):
        print("NONE")
        return

    print("TRACK", track.name, "URL:",
          session.get_track_url(serres.tracks[0].id))

    print("Token expiry:", session.expiry_time)
    print("Refreshing token, access token:", session.access_token,
          "\nAcc token type:", session.token_type, "\nRefresh token:", session.refresh_token)
    print(session.token_refresh(session.refresh_token))


future.add_done_callback(afterlogin)
