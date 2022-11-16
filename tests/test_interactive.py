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

global session


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


def renew_tokens(sessionin, refreshtkn):
    return sessionin.token_refresh(refreshtkn)


def load_oauth_sess(sessid, tkntype, acctkn, refrstkn, audioqin=None, videoqin=None):
    audioq = tidalapi.Quality.lossless
    videoq = tidalapi.VideoQuality.high

    if audioqin != None:
        if audioqin == "high":
            audioq = tidalapi.Quality.high
        if audioqin == "low":
            audioq = tidalapi.Quality.low

    if videoqin != None:
        if videoqin == "medium":
            videoq = tidalapi.VideoQuality.medium
        if videoqin == "low":
            videoq = tidalapi.VideoQuality.low

    sessionnew = tidalapi.Session(tidalapi.Config(audioq, videoq))
    islgnok = sessionnew.load_oauth_session(sessid, tkntype, acctkn, refrstkn)
    if islgnok:
        if sessionnew.check_login():
            return True, sessionnew
    return False, None


def search_tracks(sessionin, searchstr, limit=15):
    serchres = sessionin.search("track", searchstr, limit)
    tracksobj = []
    if len(serchres.tracks) == 0:
        return None
    for track in serchres.tracks:
        fullartists = []
        for oneartist in track.artists:
            fullartists.append(oneartist.name)
        trtype = "audio"
        if type(track) is tidalapi.Video:
            trtype = "video"
        trobj = {"id": track.id, "name": track.name, "artist": track.artist.name,
                 "artists": fullartists, "type": trtype, "albumname": track.album.name, "imgid": track.album.img_uuid, "albumimgurl": track.album.image}
        tracksobj.append(trobj)
    return tracksobj


def get_track_url(sessionin, trackid):
    return sessionin.get_track_url(trackid)


def get_img_from_trackid(sessionin, trackid):
    trck = sessionin.get_track(track_id=trackid)
    return trck.album.image


def search_tracks_strout(sessionin, searchstr, limit=15):
    outobj = search_tracks(sessionin, searchstr, limit)
    return json.dumps(outobj)


def afterlogin(future=None):
    albm = tidalapi.Album
    albm.image
    # return
    while True:
        operation = input("Operation (islg - check if logged in, savelg - save login to file, loadlg - load login from file, saq - set audio quality, svq - set video quality, r - renew, ptks - print tokens, stcks - search tracks, trurl - track url, timg - track img url):")
        if operation == "end":
            return
        elif operation == "r":
            print("Renewing tokens:")
            renew_tokens(session, session.refresh_token)
            print("NEW Login data:\nSession id:", session.session_id, "\nToken type:", session.token_type, "\nAccess token:",
                  session.access_token, "\nRefresh token:", session.refresh_token, "\nExpiry:", session.expiry_time)
        elif operation == "ptks":
            print("Login data:\nSession id:", session.session_id, "\nToken type:", session.token_type, "\nAccess token:",
                  session.access_token, "\nRefresh token:", session.refresh_token, "\nExpiry:", session.expiry_time)
        elif operation == "stcks":
            searchstr = input("Search text:")
            lmt = input("Limit items:")
            print("RESULT:\n"+search_tracks_strout(session, searchstr, lmt))
        elif operation == "trurl":
            trid = input("Write track id:")
            print("Track stream URL:", get_track_url(session, trid))
        elif operation == "timg":
            trid = input("Write track id:")
            print("Track image URL:", get_img_from_trackid(session, trid))


while True:
    session = None

    reloadsess = input("Reload session? (y/n):")
    if reloadsess == "y":
        sessid = input("Write session id:")
        tkntype = input("Token type:")
        acctkn = input("Access token:")
        refrstkn = input("Refresh token:")

        print("Please wait!")

        sessok, session = load_oauth_sess(sessid, tkntype, acctkn, refrstkn)
        if sessok:
            print("OK!")
            afterlogin()
            break
        print("BAD! Try again.")
    else:
        print("Creating new Oauth2 session")
        session = tidalapi.Session(tidalapi.Config(tidalapi.Quality.lossless))

        # session.login_oauth_simple()
        loginc, future = session.login_oauth()
        # future.add_done_callback(afterlogin)
        print("Login request, code:", loginc.user_code, "| Verify url:", loginc.verification_uri,
              "| Full uri to login:", loginc.verification_uri_complete, "| Verify expires in (s):", loginc.expires_in)

        print("Future result:", future.result())
        if session.check_login():
            print("OK!")
            print("Login data:\nSession id:", session.session_id, "\nToken type:", session.token_type, "\nAccess token:",
                  session.access_token, "\nRefresh token:", session.refresh_token, "\nExpiry:", session.expiry_time)
            afterlogin()
            break

    contin = input("Continue? (y/n):")
    if contin == "n":
        break

print("End!")
