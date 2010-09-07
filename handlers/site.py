# The MIT License
# 
# Copyright (c) 2008 William T. Katz
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to 
# deal in the Software without restriction, including without limitation 
# the rights to use, copy, modify, merge, publish, distribute, sublicense, 
# and/or sell copies of the Software, and to permit persons to whom the 
# Software is furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER 
# DEALINGS IN THE SOFTWARE.

"""A simple RESTful blog/homepage app for Google App Engine

This simple homepage application tries to follow the ideas put forth in the
book 'RESTful Web Services' by Leonard Richardson & Sam Ruby.  It follows a
Resource-Oriented Architecture where each URL specifies a resource that
accepts HTTP verbs.

Rather than create new URLs to handle web-based form submission of resources,
this app embeds form submissions through javascript.  The ability to send
HTTP verbs POST, PUT, and DELETE is delivered through javascript within the
GET responses.  In other words, a rich client gets transmitted with each GET.

This app's API should be reasonably clean and easily targeted by other 
clients, like a Flex app or a desktop program.
"""

__author__ = 'Kyle Conroy'

import datetime
from datetime import date, timedelta
import string
import re
import os
import cgi
import urllib
import logging
import urlparse
from wsgiref.handlers import format_date_time
from time import mktime

from google.appengine.ext import webapp
from google.appengine.ext import db
from google.appengine.api import users

from utils.external import oauth2 as oauth
from handlers import restful
from utils import authorized
from models import Status, Service, Event, Profile, AuthRequest

import config

def get_past_days(num):
    date = datetime.date.today()
    dates = []
    
    for i in range(1, num+1):
        dates.append(date - datetime.timedelta(days=i))
    
    return dates
    
class SiteHandler(restful.Controller):

    def default_parameters(self, params):
        """ Add any parameters that should be included by default """
        user = users.get_current_user()
    
        if user:
            greeting = users.create_logout_url("/")
        else:
            greeting = users.create_login_url("/")
        
    
        
        status_images = [
            [
                "tick-circle",
                "cross-circle",
                "exclamation",
                "wrench",
                "flag",
                ],
            [
                "clock",
                "heart",
                "hard-hat",
                "information",
                "lock",
                ],
            [
                "plug",
                "question",
                "traffic-cone",
                "bug",
                "broom",
                ],
            ]
            
        if "title" not in params:
            params["title"] = config.SITE["title"]
        params["version"] = { 
            "css": config.CSS_VERSION,
            "image": config.IMAGES_VERSION,
            "js": config.JS_VERSION,
            }
        params["user"] = user
        params["user_is_admin"] =  users.is_current_user_admin()
        params["login_link"] = greeting 
        params['common_statuses'] = status_images
    
        return params

    def render(self, templateparams, path):
        "Writes templateparams to a given template"
        params = self.default_parameters(templateparams)
        super(SiteHandler, self).render(params, path)

    def not_found(self):
        self.response.set_status(404)
        self.render({}, '404.html')

class NotFoundHandler(SiteHandler):
    def get(self):
        logging.debug("NotFoundHandler#get")
        self.response.set_status(404)
        self.render({}, '404.html')

class UnauthorizedHandler(webapp.RequestHandler):
    def get(self):
        logging.debug("UnauthorizedHandler#get")
        self.response.set_status(403)
        self.render({}, '403.html')

        
class BasicRootHandler(SiteHandler):
    def get(self):
        user = users.get_current_user()
        logging.debug("BasicRootHandler #get")

        q = Service.all()
        q.order("name")
        services = q.fetch(100)
        
        p = Status.all()
        p.order("severity")
        
        past = get_past_days(5)
        
        td = {}
        td["services"] = q.fetch(100)
        td["statuses"] = p.fetch(100)
        td["past"] = past
        td["default"] = Status.default()

        self.render(td, 'site/index.html')

class BasicServiceHandler(SiteHandler):

    def get(self, service_slug, year=None, month=None, day=None):
        user = users.get_current_user()
        logging.debug("BasicServiceHandler #get")

        service = Service.get_by_slug(service_slug)

        if not service:
            self.not_found()
            return

        events = service.events
        show_admin = False

        try: 
            if day:
                start_date = date(int(year),int(month),int(day))
                end_date = start_date + timedelta(days=1)
            elif month:
                start_date = date(int(year),int(month),1)
                days = calendar.monthrange(start_date.year, start_date.month)[1]
                end_date = start_date + timedelta(days=days)
            elif year:
                start_date = date(int(year),1,1)
                end_date = start_date + timedelta(days=365)
            else:
                start_date = None
                end_date = None
                show_admin = True
        except ValueError:
            self.not_found()
            return
            
        if start_date and end_date:
            events.filter('start >= ', start_date).filter('start <', end_date)

        events.order("-start")

        td = {}
        td["service"] = service
        td["events"] = events.fetch(100)
        td["start_date"] = start_date
        td["end_date"] = end_date

        self.render(td, 'site/service.html')
        
class DocumentationOverview(SiteHandler):
    
    def get(self):
        td = {}
        td["overview_selected"] = True
        self.render(td, 'documentation/overview.html')

class DocumentationRest(SiteHandler):
    
    def get(self):
        td = {}
        td["rest_selected"] = True
        self.render(td, 'documentation/restapi.html')

class DocumentationExamples(SiteHandler):
    
    def get(self):
        td = {}
        td["example_selected"] = True
        self.render(td, 'documentation/examples.html')

class TestHandler(SiteHandler):
    
    def get(self):
        self.render({},'admin/test.html')
        
