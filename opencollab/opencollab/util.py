import ConfigParser

def loadCredsFromConfig(wiki, filenames, section="creds"):
    configparser = ConfigParser.ConfigParser()
    if not configparser.read(filenames):
        return False

    try:
        username = configparser.get(section, "username")
        password = configparser.get(section, "password")
    except ConfigParser.NoOptionError:
        return False

    wiki.setCredentials(username, password)
    return True
