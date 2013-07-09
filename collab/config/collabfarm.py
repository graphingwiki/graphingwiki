from MoinMoin.config.multiconfig import DefaultConfig

class FarmConfig(DefaultConfig):
    data_underlay_dir = '/srv/wikis/collab/underlay'
    url_prefix_static = '/moin_static'
    user_dir = '/srv/wikis/collab/user'
    cache_dir = '/srv/wikis/collab/cache'

    shared_intermap = '/srv/wikis/collab/config/intermap.txt'

    # Mail setup, configure if you need mail support
    #mail_smarthost = ''
    #mail_from = ''
    # Invite default domain, configure if you need invite
    #invite_sender_default_domain = ''

    navi_bar = [
        u'CollabList',
        u'%(page_front_page)s',
        u'RecentChanges',
        u'FindPage',
        u'HelpContents',
    ]
    page_front_page = u"FrontPage"

    theme_default = 'opencollab'
    language_default = 'en'

    page_category_regex = ur'(?P<all>Category(?P<key>(?!Template)\S+))'
    page_dict_regex = ur'(?P<all>(?P<key>\S+)Dict)'
    page_group_regex = ur'(?P<all>(?P<key>\S+)Group)'
    page_template_regex = ur'(?P<all>(?P<key>\S+)Template)'

    show_hosts = 1
    show_interwiki = 0

    logo_string = u''
    #logo_string = u'<a href=\"/collab/\"><img src=\"/img/wiki-logo.gif\" alt=\"Back to Collab Home\"></a>'

    chart_options = {'width': 600, 'height': 300}

    from MoinMoin.auth import GivenAuth
    auth = [GivenAuth(autocreate=False)]
    auth_methods_trusted = ['given', 'xmlrpc_applytoken']
    password_scheme = '{SHA}'

    cookie_path = '/collab/'
    cookie_httponly = True
    # enforce lifetime of 24h, negative value ignores 'remember_me' setting
    cookie_lifetime = (0, -24)

    # allow refresh
    refresh = ( 1, 'external' )

    # allow xmlrpc
    actions_excluded = []

    # uncomment this if you want to allow Moin package installation
    # packagepages_actions_excluded = []

    # disable reverse DNS
    log_reverse_dns_lookups = False

    # some user pref defaults
    user_checkbox_defaults = { 'edit_on_doubleclick': 0,
                               'show_nonexist_qm': 1,
                               'show_page_trail': 1,
                               'want_trivial': 0 }

    # remove from user prefs
    user_checkbox_remove = [ 'disabled' ]
    #user_form_remove = [ 'password', 'password2' ]
    user_form_disable = [ 'name', 'aliasname', 'email' ]

    # remove logout button
    show_login = 0

    # tame down surge protection
    surge_action_limits = None

    # let in bigger zips
    unzip_single_file_size = 100.0 * 1000**2
    unzip_attachments_space = 500.0 * 1000**2
    unzip_attachments_count = 500

    # default ACLs
    acl_rights_valid = ["read", "write", "delete", "revert", "admin", "invite"]
    acl_rights_default = u"Trusted:admin,read,write,delete,revert,invite" +\
        " collab:admin,read,write All:"

    # Add your superusers to these lines
    acl_rights_before  = u"collab:read,write,admin,delete,revert,invite"
    superuser = ['collab']

    # for standalone
    port = 10010
    interface = ''

    plugin_dirs = list()

    import os

    # Use graphingwiki if installed
    try:
        from graphingwiki import install_hooks
        from graphingwiki import __path__ as graphingwiki_dir
        install_hooks()
        for gdir in graphingwiki_dir:
            plugin_dirs.append(os.path.join(gdir, 'plugin'))
    except ImportError:
        pass

    try:
        from collabbackend import __path__ as collabbackend_dir
        for cdir in collabbackend_dir:
            plugin_dirs.append(os.path.join(cdir, 'plugin'))
    except ImportError:
        pass

    import mimetypes
    mimetypes.add_type('application/x-x509-ca-cert', '.crt', True)
    mimetypes.add_type("application/x-pcap", ".pcap", True)
    mimetypes.add_type("text/plain", ".scm", True)
    mimetypes.add_type('video/mp4', '.mp4', True)
    mimetypes.add_type('text/csv', '.csv', True)

    #mimetypes_xss_protect.remove('application/x-shockwave-flash')
    #mimetypes_embed.add('application/x-shockwave-flash')

    collab_basedir = '/srv/wikis/collab/htdocs'
    collab_baseurl = 'https://localhost/collab/'
    collab_chat_bosh = '/bosh/'
    collab_chat_creds = '/collab/?action=authcredentials'
    # Set your xmpp domain here if autodetection fails
    #collab_chat_domain = ''

    gwiki_geoip_path = '/etc/local/collab/GeoIPCity.dat'

    gwikivariables = {'GWIKITEST': 'I am the bestest!'}

    #invite_sender_default_domain = ''
    #invite_new_template = 'InviteNewTemplate'
    #invite_old_template = 'InviteOldTemplate'
    invite_group_default = 'AccessGroup'

    stylesheets = [
        ('all', url_prefix_static + '/gwikicommon/css/common.css')
    ]

    html_head = '''
    <link rel="stylesheet" type="text/css" charset="utf-8" media="all" href="%(url_prefix_static)s/arnica/css/text_x_arnica.css">
    <link rel="stylesheet" type="text/css" charset="utf-8" media="all" href="%(url_prefix_static)s/arnica/css/arnica_slides.css">
    <!-- css only for MSIE browsers -->
    <!--[if IE]>
    <link rel="stylesheet" type="text/css" charset="utf-8" media="all" href="%(url_prefix_static)s/arnica/css/msie_arnica_slides.css">
    <![endif]-->
    <!-- Fix for wikis in intranet zone for IE -->
    <meta http-equiv="X-UA-Compatible" content="IE=edge" />
    ''' % {"url_prefix_static": url_prefix_static}

    for script in ['js/mootools-core-yc.js', \
                   'js/mootools-more-yc.js', \
                   'js/gwiki-common.js', \
                   'simile/timeline/timeline_ajax/simile-ajax-api.js', \
                   'simile/timeline/timeline_js/timeline-api.js?bundle=true']:
        html_head += '<script src="%s" type="text/javascript"></script>' \
                     % (url_prefix_static + '/gwikicommon/' + script)

    ## for htdocs/collabcommon

    # html_head = '' # omit if you already have something

    for script in ['js/strophe.js', \
                   'js/chat.js']:
        html_head += '<script src="%s" type="text/javascript"></script>' \
                     % (url_prefix_static + '/collabcommon/' + script)

    # stylesheets = [] # omit if you already have something

    for type, style in [('all', 'chat.css'), \
                        ('all', 'common.css'), \
                        ('screen', 'screen.css'), \
                        ('print', 'print.css'), \
                        ('projection', 'projection.css')]:
        stylepath = url_prefix_static + '/collabcommon/css/' + style
        stylesheets.append((type, stylepath))
