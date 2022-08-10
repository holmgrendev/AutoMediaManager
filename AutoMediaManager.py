from datetime import datetime
import json
import logging
import os
import sys
import re
import urllib.parse as urlp
import urllib.request as rq
import shutil

cwd = os.getcwd()
cfg = False
dat = False

def main():
    
    global cfg
    cfgPath = os.path.join(cwd, "config.json")

    global dat
    datPath = os.path.join(cwd, "data.json")

    ### Load config file

    try:
        log("Trying to load config file \"" + cfgPath + "\"", "I")

        with open(cfgPath) as file:
            cfg = json.load(file)

    except json.JSONDecodeError:
        log("Couldn't parse config file, is the file correctly formatted?", "E")
        log("Terminating", "E")
        sys.exit(0)
    
    except FileNotFoundError:
        log("Couldn't find config file", "E")
        log("Copy and rename the file \"config.sample.json\" to \"config.json\" and make neccesary changes", "E")
        log("Terminating", "E")
        sys.exit(0)
    
    except:
        log("Problem loading config file", "E")
        log("Terminating", "E")
        sys.exit(0)

    log("Config file was successfully loaded", "I")


    ### Load data file

    try:
        log("Trying to load data file \"" + datPath + "\"", "I")

        with open(datPath) as file:
            dat = json.load(file)

    except json.JSONDecodeError:
        log("Couldn't parse data file, have you made any bad changes to the file?", "E")
        log("Terminating", "E")
        sys.exit(0)
    
    except FileNotFoundError:
        log("Couldn't find data file, have you by any chance deleted it?", "E")
        log("Terminating", "E")
        sys.exit(0)
    
    except:
        log("Problem loading data file", "E")
        log("Terminating", "E")
        sys.exit(0)
    
    log("Data file was successfully loaded", "I")


    ### Check if user has defined paths in config file

    if not "directory" in cfg or len(cfg["directory"]) == 0:
        log("No specified directory in config file", "E")
        log("Nothing here to do", "E")
        log("Terminating", "E")
        sys.exit(0)


    ### Check if TMDB should be used to validate filenames

    useTMDB = False
    #log("Checking connection to TMDB", "I")
    if checkTMDB():
        useTMDB = True
    
    
    ### Loop trough all defined input directories in config file

    for dir in cfg["directory"]:

        ### Check if media type is correctly specified

        if not "media" in dir or not dir["media"] or not dir["media"] in ["movies", "shows"]:
            log("Media type was not specified for the path in gonfig file", "E")
            log("Update \"media\" in config file and set it to either \"movies\" or \"shows\"", "E")
            log("Skipping directory", "E")
            continue

        log("Media type was specified as: " + dir["media"], "I")

        ### Check if action is correctly specified

        if not "action" in dir or not dir["action"] or not dir["action"] in ["cleanmove", "cleancopy", "copy", "move", "symlink"]:
            log("Action was not specified for the path in gonfig file", "E")
            log("Update \"action\" in config file and set it to either \"copy\", \"move\", \"cleanmove\" or \"symlink\"", "E")
            log("Skipping directory", "E")
            continue
        
        log("Action type was specified as: " + dir["action"], "I")


        ### Check if input directory is valid

        if "input" in dir and os.path.isdir(dir["input"]):
            scanDir = os.path.normpath(dir["input"])
            log("Using \"" + scanDir + "\" for the scan", "I")

        else:
            log("Couldn't find the specified directory (\"" + dir["input"] + "\")", "E")
            log("Skipping directory", "E")
            continue
        
        ### Check if output directory is specified

        if not "output" in dir or not dir["output"]:
            log("No output directory is properly defined", "I")
            log("Using same directory as input (\"" + scanDir + "\") for the output", "I")
            outDir = scanDir
        
        else:
            outDir = os.path.normpath(dir["output"])
            log("Using \"" + outDir + "\" for the output", "I")
        

        ### Scan directory
        scan = scanDirectory(scanDir)
        

        ### Check if the scan was successful

        if not scan:
            log("Something went wrong scanning the specified directory", "E")
            log("Skipping directory", "E")
            continue
        
        if len(scan) == 0:
            log("Problem occured reading directories", "E")
            log("Terminating", "E")
            sys.exit(0)
        

        log("Successfully scanned directories", "I")
        log("Organizing files", "I")


        ### Organize files

        library = {}

        for path in scan:
            mediaFile = solveMediaFile(path, scanDir, dir["media"])

            ### Skip file if it were un-solve-able
            if not mediaFile:
                continue

            sortTitle = next(iter(mediaFile))
            
            ### If sortTitle wasn't already in library, add it
            ### I have tried:
            ### library[sortTitle] = mediaFile[sortTitle]
            ### 
            ### and the just appended the content if sortTitle already existed:
            ### library[sortTitle]["content"].append(mediaFile[sortTitle]["content"])
            ###
            ### But it creates i "two depth" list
            ### "content": [[{...}, {...}]]
            ### 
            ### But adding everything manual seems to work, i have no idea why

            if not sortTitle in library:
                library[sortTitle] = {"title": mediaFile[sortTitle]["title"]}

                ### Check if mediaFile has a year specified, the plan is in the future to be able to return movies without year if no year was found in title, and check it with TMDB later
                if mediaFile[sortTitle]["year"]:
                    library[sortTitle]["year"] = mediaFile[sortTitle]["year"]
                
                ### Chek if season and episodes exists in mediaFile
                if "season" in mediaFile[sortTitle] and "episode" in mediaFile[sortTitle]:
                    library[sortTitle]["season"] = mediaFile[sortTitle]["season"]
                    library[sortTitle]["episode"] = mediaFile[sortTitle]["episode"]
                
                library[sortTitle]["content"] = []
            
            ### Add content to library
            library[sortTitle]["content"].append(mediaFile[sortTitle]["content"])


        ### Check if the organizing of the library went well

        if len(library) == 0:
            log("Problem occured while organizing files", "E")
            log("Terminating", "E")
            sys.exit(0)
        

        log("Files successfully organized", "I")


        ### Update filenames using TMDB
        if useTMDB:
            log("Using TMDB to update media", "I")

            updateLibrary = {}
            
            ### Go trough Medie
            for media in library:
                
                ### Update media
                updateMedia = getTMDBInfo(library[media], dir["media"])

                ### Add the newly discovered updates to the new library
                if updateMedia:
                    log("Updating media", "I")
                    updateLibrary[media] = updateMedia

                    if "year" in updateMedia and updateMedia["year"]:
                        updateLibrary[media]["year"] = updateMedia["year"]
                
                ### ... or use the old info
                else:
                    updateLibrary[media] = library[media]
                
            library = updateLibrary
        
        
        ### create a new path for all media files and return
        updateLibrary = []

        for media in library:
            updateMedia = getPaths(library[media], dir["media"], outDir)
            
            if updateMedia:
                updateLibrary = updateLibrary + updateMedia
            


        #print(json.dumps(updateLibrary))

        ### do whatever user specified in config

        ### Create symlinks
        if dir["action"] == "symlink":
            for media in updateLibrary:

                if os.path.isfile(media["newPath"]):
                    log("\"" + media["newPath"] + "\" already exists", "E")
                    continue

                ### Create directories
                try:
                    newDir = (os.path.split(media["newPath"]))[0]
                    if not os.path.isdir(newDir):
                        os.makedirs(newDir)
                except:
                    log("Failed creating directories for: \"" + media["path"] + "\"", "E")
                    log("Do you have permissions?", "E")
                    continue


                log("Creating a symbolic link from \"" + media["path"] + "\" to \"" + media["newPath"] + "\"", "E")

                try:
                    os.symlink(os.path.join(media["path"]), os.path.join(media["newPath"]))
                except Exception as e:
                    log("Failed creating a symbolic link from \"" + media["path"] + "\" to \"" + media["newPath"] + "\"", "E")
                    log("Do you have permissions?", "E")
                    print(e)
                    continue

                log("Created a symbolic link from \"" + media["path"] + "\" to \"" + media["newPath"] + "\"", "E")
                

        if dir["action"] == "copy" or dir["action"] == "cleancopy":
            for media in updateLibrary:

                if os.path.isfile(media["newPath"]):
                    log("\"" + media["newPath"] + "\" already exists", "E")
                    continue

                ### Create directories
                try:
                    newDir = (os.path.split(media["newPath"]))[0]
                    if not os.path.isdir(newDir):
                        os.makedirs(newDir)
                except:
                    log("Failed creating directories for: \"" + media["path"] + "\"", "E")
                    log("Do you have permissions?", "E")
                    continue


                log("Copying \"" + media["path"] + "\" to \"" + media["newPath"] + "\"", "I")

                try:
                    shutil.copyfile(os.path.join(media["path"]), os.path.join(media["newPath"]))
                except Exception as e:
                    log("Failed copying \"" + media["path"] + "\" to \"" + media["newPath"] + "\"", "E")
                    log("Do you have permissions?", "E")
                    print(e)
                    continue

                log("Successfully copied \"" + media["path"] + "\" to \"" + media["newPath"] + "\"", "I")


        if dir["action"] == "move" or dir["action"] == "cleanmove":
            for media in updateLibrary:

                if os.path.isfile(media["newPath"]):
                    log("\"" + media["newPath"] + "\" already exists", "E")
                    continue

                ### Create directories
                try:
                    newDir = (os.path.split(media["newPath"]))[0]
                    if not os.path.isdir(newDir):
                        os.makedirs(newDir)
                except:
                    log("Failed creating directories for: \"" + media["path"] + "\"", "E")
                    log("Do you have permissions?", "E")
                    continue


                log("Moving \"" + media["path"] + "\" to \"" + media["newPath"] + "\"", "I")

                try:
                    shutil.move(os.path.join(media["path"]), os.path.join(media["newPath"]))
                except Exception as e:
                    log("Failed moving \"" + media["path"] + "\" to \"" + media["newPath"] + "\"", "E")
                    log("Do you have permissions?", "E")
                    print(e)
                    continue

                log("Successfully moved \"" + media["path"] + "\" to \"" + media["newPath"] + "\"", "I")
            
        if dir["action"] == "cleanmove" or dir["action"] == "cleanmove":
            log("Better start cleaning", "I")

            ### Cleaning (removing contents of) the input directory but skipping the directories not effected by the move
            for media in updateLibrary:
                oldDir = (os.path.split(media["path"]))[0]

                if oldDir == scanDir or not os.path.isdir(oldDir): continue

                
                log("Removing \"" + oldDir + "\" and its content", "I")

                try:
                    shutil.rmtree(oldDir)
                except Exception as e:
                    log("Failed removing \"" + oldDir + "\" and its content", "E")
                    log("Do you have permissions?", "E")
                    print(e)
                    continue
                
                log("Removed \"" + oldDir + "\" and its content", "I")
            
        log("Finished working on \"" + scanDir + "\"", "I")
    log("Finished with everything, going to slee .. zZzzzzZZZzz", "I")
            



def getPaths(media, mediaType, outDir):

    ### create baseName and pathName for movies
    if mediaType == "movies":
        baseName = media["title"] + " (" + media["year"] + ")"
        pathName = baseName

    ### create baseName and pathName for shows
    if  mediaType == "shows":
        baseName = media["title"]

        ### Check wether year is present or not
        if "year" in media and media["year"]:
            baseName = baseName + " (" + media["year"] + ")"

        ### Create correct naming for episodes (check if multiple episodes in one file)
        tempEpisode = media["episode"]
        
        if type(tempEpisode) == list:
            tempEpisode = "-E".join(tempEpisode)
        

        pathName = os.path.join(baseName, baseName + " S" + media["season"], baseName + " S" + media["season"] + "E" + tempEpisode)
        baseName = baseName + " S" + media["season"] + "E" + tempEpisode
    
    ### Create new paths for media file
    updateContent = []
    for item in media["content"]:

        tempItem = item

        tempItem["newPath"] = os.path.join(outDir, pathName, baseName + "." + item["options"])
        del item["options"]

        updateContent.append(tempItem)
    
    return updateContent



def getTMDBInfo(media, mediaType):
    
    if mediaType == "movies":

        ### Define url parameters
        urlParams = {"api_key": cfg["tmdbKey"], "query": media["title"]}

        if media["year"]:
            urlParams["year"] = media["year"]


        ### Try to get info from TMDB API

        try:
            log("Checking \"" + media["title"] + "\" with TMDB", "I")
            r = rq.urlopen("https://api.themoviedb.org/3/search/movie?" + urlp.urlencode(urlParams))

        except:
            log("Something went wrong trying to reach TMDB", "E")
            return False
        

        ### Check if we got a good response
        if not (str(r.status)[0]) == "2":
            log("Something went wrong trying to reach TMDB, status code: " + str(r.status), "E")
            return False
        

        ### Load fetched data
        movieData = json.loads(r.read())


        ### check if any results was found
        if len(movieData["results"]) == 0:
            log("No results found for \"" + media["title"] + "\" at TMDB", "I")
            return False


        log("Found info for \"" + media["title"] + "\" on TMDB: \"" + movieData["results"][0]["title"] + "\"", "I")


        ### Update media info
        out = {"title": re.sub(r"[^\w\-_\. ]", "", movieData["results"][0]["title"]), "year": str((datetime.strptime(movieData["results"][0]["release_date"], "%Y-%m-%d")).year), "content": media["content"]}

        return out


    if mediaType == "shows":
        
        ### Define url parameters
        urlParams = {"api_key": cfg["tmdbKey"], "query": media["title"]}


        ### Try to get info from TMDB API

        try:
            log("Checking \"" + media["title"] + "\" with TMDB", "I")
            r = rq.urlopen("https://api.themoviedb.org/3/search/tv?" + urlp.urlencode(urlParams))

        except:
            log("Something went wrong trying to reach TMDB", "E")
            return False
        

        ### Check if we got a good response
        if not (str(r.status)[0]) == "2":
            log("Something went wrong trying to reach TMDB", "E")
            return False
        

        ### Load fetched data
        showData = json.loads(r.read())


        ### check if any results was found
        if len(showData["results"]) == 0:
            log("No results found for \"" + media["title"] + "\" at TMDB", "I")
            return False
        

        ### Update media info
        out = {"title": re.sub(r"[^\w\-_\. ]", "", showData["results"][0]["name"]), "season": media["season"], "episode":  media["episode"]}


        if showData["results"][0]["first_air_date"]:
            out["year"] = str((datetime.strptime(showData["results"][0]["first_air_date"], "%Y-%m-%d")).year)
        
        out["content"] = media["content"]

        log("Found info for \"" + media["title"] + "\" on TMDB: \"" + showData["results"][0]["name"] + "\"", "I")
        return out
    
    return False

def scanDirectory(path):
    
    ### Get content of directory

    try:
        log("Scanning \"" + path + "\"", "I")
        pathContent = os.scandir(path)

    except:
        log("Something went wrong when trying to scan \"" + path + "\"", "E")
        return False
    

    ### Check if anything was found
    if not pathContent:
        log("Something went wrong when trying to scan \"" + path + "\"", "E")
        return False

    ### Go trough the content in directory

    content = []

    for entry in pathContent:
        log("Checking \"" + entry.path + "\"", "I")

        if entry.is_symlink():

            ### Is a symbolic link, we are not doing that (currently)
            log("\"" + entry.name + "\" is a symbolic link, skipping", "I")
            continue


        if entry.is_dir(follow_symlinks=False):
            
            ### Is a directory, start recursive scanning
            #log("\"" + entry.name + "\" is a directory, start scanning", "I")
            result = scanDirectory(entry.path)

            ### Check wether te scan of the directory was successful
            if not result:
                log("Problem occured when trying to scan \"" + entry.name + "\", skipping", "E")
                continue
            
            ### Add files from the scan to the list
            #log("\"" + entry.name + "\" successfully scanned, adding files to list", "I")
            content += result
    

        if entry.is_file():

            ### Is a file (yaay), Check if the file is a valid media file
            if not isMediaFile(entry.name):

                ### Was not a valid media file
                log("\"" + entry.name + "\" is not a media file, skipping", "E")
                continue
            
            ### Add file to the list
            content.append(entry.path)
  
  
    return content


def isMediaFile(fileName):

    ### Get file ending
    fileEnding = (fileName.split("."))[-1]

    ### Check if file ending exists in data file
    if fileEnding in dat["filetypes"]['video']:
        #log("We have identified \"" + fileName + "\" as a video file", "I")
        return "video"
    
    if fileEnding in dat["filetypes"]['subtitle']:
        #log("We have identified \"" + fileName + "\" as a subtitle file", "I")
        return "subtitle"


    ### Return false if file ending wasn't found in data.json
    #log("We have not been able to identify \"" + fileName + "\" as a proper media file", "I")
    return False


def checkTMDB():

    ### Check if user has specified that we should check with TMDB
    if not "tmdbConfirm" in cfg or not cfg["tmdbConfirm"]:
        log("tmdbConfirm in config is disabled", "I")
        log("Skipping TMDB...", "I")
        return False


    ### Check if user has entered an API-Key for TMDB
    if not "tmdbKey" in cfg or not cfg["tmdbKey"]:
        log("tmdbKey (API-Key) is not defined", "I")
        log("Please enter a valid API-Key or set tmdbConfirm to false", "I")
        log("Skipping TMDB...", "I")
        return False
    

    ### Send a request to the TMDB API with the search of a movie named "cars"
    try:
        urlParams = {"api_key": cfg["tmdbKey"], "query": "cars"}
        log("Connecting to TMDB", "I")
        r = rq.urlopen("https://api.themoviedb.org/3/search/movie?" + urlp.urlencode(urlParams))

    except:
        log("Something went wrong trying to connect to TMDB", "E")
        log("Do you have entered a valid API-Key in config or an internet connection?", "E")
        return False
    

    ### Check if TMDB sent a successfull response
    if not (str(r.status)[0]) == "2":
        log("Something went wrong trying to connect to TMDB", "E")
        log("Looks like TMDB is not responding", "E")
        log("HTTP status code: " + r.status, "E")
        return False
    

    ### Read the result an parse it to python dictionary
    result = json.loads(r.read())


    ### Check if we got a non successfull response
    if "success" in result and result["success"] == False:
        log("Something went wrong trying to connect to TMDB", "E")
        log("TMDB status message: " + result["status_message"], "E")
        return False
    

    ### Check if we got any results from the API (We should have), otherwise, it could be a problem with TMDBs API
    if "total_results" in result and result["total_results"] > 0:
        log("Successfully connected to TMDB", "I")
        return True
    

    log("Something went wrong trying to connect to TMDB", "E")
    log("Unknown error,", "E")
    return False


def solveMediaFile(path, scanDir, mediaType):
    
    foundMedia = False
    
    if mediaType == "movies":
        ### Get current year and create a regular expression wich can file years between 1900 to next year (next year could be max 2099), file a bug report if the next ear is above 2100
        nextYear = str(datetime.now().year+1)
        rxMedia = "^(.*)(19[0-9]{2}|20[0-"+str(int(nextYear[2])-1)+"][0-9]|20"+nextYear[2]+"[0-"+nextYear[3]+"])"
    
    if mediaType == "shows":
        rxMedia = "([a-zA-Z0-9_\. \-]*).*s([0-9]{2}).?(?:e([0-9]{2}).?e([0-9]{2})[^a-zA-Z0-9]|e([0-9]{2}).?([0-9]{2})[^a-zA-Z0-9]|e([0-9]{2}))"
        
    #remove all directories below scanDir
    pathStrip = [x for x in (os.path.normpath(path)).split(os.sep) if x not in os.path.normpath(scanDir).split(os.sep)]
    

    ### Check file name and if needed all directories leading up to the file
    for value in reversed(pathStrip):

        tryMedia = re.search(rxMedia, value, re.IGNORECASE)

        if tryMedia:
            foundMedia = True
            #log("Found media file: " + value, "I")
            break
    
    ### Check if we were able to resolve file name
    if not foundMedia:
        log("Could not resolve media file: " + path, "I")
        return False


    ### Sanitize movie title
    title = (" ".join(((tryMedia.group(1)).replace("_", " ").replace(".", " ").replace("-", " ").replace("(", " ").replace(")", " ")).split())).lower()

    ### Remove empty groups from the file name resolving
    cleanGroups = [x for x in tryMedia.groups() if x is not None]

    ### Get language, language codes for subtitles and check if file is parted
    options = getMediaOptions((os.path.split(path))[1])

    ### Check wether getting options was successfull or not
    if not options:
        return False
    
    if mediaType == "movies":
        year = False
        if len(cleanGroups) == 2:
            year = cleanGroups[1]
        
        ### Create a sorting title, used to group files belonging to the same movie
        if not year:
            return False
        
        sortTitle = title + " (" + year + ")"
        
        return {sortTitle: {"title": title, "year": year, "content": {"options": options, "path": path}}}
    
    
    if mediaType == "shows":
        season = cleanGroups[1]
        episode = cleanGroups[2]
        sortTitle = title + " S" + season + "E" + episode

        if len(cleanGroups) == 4:
            episode = [cleanGroups[2], cleanGroups[3]]
            sortTitle = sortTitle + "-E" + cleanGroups[3]
        

        return {sortTitle: {"title": title, "season": season, "episode": episode, "year": False, "content": {"options": options, "path": path}}}


def getMediaOptions(fileName):
    ### Find language, language codes for subtitles and check if file is parted
    
    ### Get file type
    fileType = isMediaFile(fileName)

    ### Split filename into parts
    #parts = fileName.split(".")
    parts = re.split('[^a-zA-Z0-9]+', fileName)

    ### get file ending
    fileEnding = parts.pop()

    rxSplit = "|".join(dat["split"])
    languageOptions = ""
    language = ""
    split = ""
    
    for part in reversed(parts):
        part = part.lower()

        ### Check language and language options for subtitles
        if fileType == "subtitle":
            if part in dat["languageOptions"]:
                languageOptions += part + "."
                continue


            findLanguage = [g for g in dat["languages"] if part in dat["languages"][g] or part == g]
            if findLanguage:
                language = findLanguage[0] + "."
                continue
        
        ### Check if file is splitted into pieces
        searchSplit = re.search("(?:" + rxSplit + ")([0-9])$", part)

        if searchSplit and searchSplit.group(1):
            split = "cd" + searchSplit.group(1) + "."
            continue

        ### Try to determine if the file is only a sample
        if part == "sample":
            return False

        ### If none of the conditions are met, its safe to say that we are done here
        break

    return split + language + languageOptions + fileEnding


def log(msg, level="I"):

    ### Try to resolve level
    levels = {
        "C": 50,
        "CRITICAL": 50,
        "E": 40,
        "ERROR": 40,
        "W": 30,
        "WARNING": 30,
        "I": 20,
        "INFO": 20,
        "D": 10,
        "DEBUG": 10
    }

    level = str(level).upper()

    if level in levels:
        l = levels[level]
    else:
        l = 20
    
    logDir = os.path.join(cwd, "logs")
    
    ### Create log directory
    if not os.path.isdir(logDir):
        os.makedirs(logDir)
    
    ### Configure logger
    logging.basicConfig(filename=os.path.join(logDir, f"{datetime.today().strftime('%Y%m%d')}.log"), filemode="a", format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=10)
    
    ### Log
    logging.log(l, msg)


if __name__ == "__main__":
    main()
