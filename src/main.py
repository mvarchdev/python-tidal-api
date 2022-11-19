import calendar
from datetime import tzinfo
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
import pytz

socket_path = "./socketfolder/tidalapi.sock"


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
    try:
        return sessionin.get_track_url(trackid)
    except:
        return "err"


def get_img_from_trackid(sessionin, trackid):
    try:
        trck = sessionin.get_track(track_id=trackid)
        return trck.album.image, trck.album.img_uuid
    except:
        return "err", None


def search_tracks_strout(sessionin, searchstr, limit=15):
    try:
        outobj = search_tracks(sessionin, searchstr, limit)
        return json.dumps(outobj)
    except:
        return "err"


def process_req(datain="", connsock=socket.socket()):
    if datain == "":
        return
    parsed = json.loads(datain)

    session = tidalapi.Session()

    reqtype = parsed["reqtype"]

    if reqtype != "oauthlogin":
        sessok, session = load_oauth_sess(
            parsed["sessid"], parsed["tkntype"], parsed["acctkn"], None, parsed["audioq"] if "audioq" in parsed else None, parsed["videoq"] if "videoq" in parsed else None)
        if not sessok:
            connsock.send(json.dumps({"status": "err_old"}).encode())

    if reqtype == "search":
        print("Search request!")
        res = search_tracks_strout(
            session, parsed["searchstr"], parsed["limit"])
        if res == "err":
            print("ERROR")
            connsock.send(json.dumps({"status": "err"}).encode())
        else:
            print("OK Getting search results, sending")
            connsock.send(json.dumps({"status": "ok", "result": res}).encode())
        None
    elif reqtype == "audiourl":
        print("Audio stream url request!")
        res = get_track_url(session, parsed["trid"])
        if res == "err":
            print("ERROR")
            connsock.send(json.dumps({"status": "err"}).encode())
        else:
            print("OK Getting URL, sending")
            connsock.send(json.dumps(
                {"status": "ok", "streamurl": res}).encode())

        None
    elif reqtype == "videourl":
        None
    elif reqtype == "imgurl":
        print("Image url request!")
        res, imgid = get_img_from_trackid(session, parsed["trid"])
        if res == "err":
            print("ERROR")
            connsock.send(json.dumps({"status": "err"}).encode())
        else:
            print("OK Getting URL, sending")
            connsock.send(json.dumps(
                {"status": "ok", "imgid": imgid, "imgurl": res}).encode())
    elif reqtype == "renewtkns":
        print("Request for token renew!")
        if session.token_refresh(parsed["refrtkn"]):
            print("Oauth2 RENEW - OK, sending new login data")
            utcexpiryts = calendar.timegm(session.expiry_time.astimezone(pytz.UTC).timetuple())
            newdata = json.dumps({"status": "ok", "tkntype": session.token_type,
                                  "acctkn": session.access_token, "expiry": utcexpiryts})
            print("Renew OK, sending NEW login data")
            connsock.send(newdata.encode())
        else:
            connsock.send(json.dumps({"status": "err_renewing"}).encode())
    elif reqtype == "oauthlogin":
        print("Oauth2 login request")
        try:
            loginc, future = session.login_oauth()
            outobj = {"status": "ok", "verifyuri": loginc.verification_uri_complete,
                      "expverifsec": loginc.expires_in}
            connsock.send(json.dumps(outobj).encode())
            futres = future.result()
            if futres != None:
                connsock.send(json.dumps({"status": "err"}).encode())
            else:
                print("Oauth2 LOGIN - OK, sending login data")
                utcexpiryts = calendar.timegm(session.expiry_time.astimezone(pytz.UTC).timetuple())
                newdata = json.dumps({"status": "ok", "sessid": session.session_id, "tkntype": session.token_type,
                                     "acctkn": session.access_token, "refrtkn": session.refresh_token, "expiry": utcexpiryts})
                print("Login OK sending LOGIN DATA!")
                connsock.send(newdata.encode())
        except:
            if future.result() == TimeoutError:
                print("ERROR: Timeout")
                connsock.send(json.dumps({"status": "timeout"}).encode())
            elif future.result() != None:
                print("ERROR:", future.result())
                connsock.send(json.dumps({"status": "err"}).encode())
            else:
                print("ERROR")
                connsock.send(json.dumps({"status": "err"}).encode())
    print("Request completed, end!")
    return


def init():
    try:
        os.unlink(socket_path)
    except OSError:
        if os.path.exists(socket_path):
            raise

    # Create a UDS socket
    global uds_socket
    uds_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

    # Bind the socket to the port
    print('Starting up UDS socket on %s' % socket_path, file=sys.stderr)
    uds_socket.bind(socket_path)

    uds_socket.listen(20)

    return


def handleconn(conn, client_addr):
    datafrom = conn.recv(4096)
    process_req(datafrom, conn)
    conn.close()
    print("Socket closed!")


def mainprog():
    while True:
        # Wait for a connection
        print('Waiting for a connection', file=sys.stderr)
        connection, client_address = uds_socket.accept()
        try:
            print('New connection from', client_address, file=sys.stderr)

            newthr = threading.Thread(
                target=handleconn, args=(connection, client_address,), daemon=True)
            newthr.start()
        except:
            print("Error occured while connecting!")
    return


init()
mainprog()
