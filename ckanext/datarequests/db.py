# -*- coding: utf-8 -*-

# Copyright (c) 2015-2016 CoNWeT Lab., Universidad Politécnica de Madrid

# This file is part of CKAN Data Requests Extension.

# CKAN Data Requests Extension is free software: you can redistribute it and/or
# modify it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# CKAN Data Requests Extension is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with CKAN Data Requests Extension. If not, see <http://www.gnu.org/licenses/>.

import sqlalchemy as sa
import uuid
import logging
import ckan.plugins.toolkit as tk
from ckanext.datarequests import constants

from sqlalchemy import func, MetaData, DDL
from sqlalchemy.sql.expression import or_

log = logging.getLogger(__name__)
DataRequest = None
Comment = None
DataRequestFollower = None


def uuid4():
    return str(uuid.uuid4())


def init_db(model):

    global DataRequest
    global Comment
    global DataRequestFollower
    global closing_circumstances_enabled
    closing_circumstances_enabled = tk.h.closing_circumstances_enabled

    if DataRequest is None:

        class _DataRequest(model.DomainObject):

            @classmethod
            def get(cls, **kw):
                '''Finds all the instances required.'''
                query = model.Session.query(cls).autoflush(False)
                return query.filter_by(**kw).all()

            @classmethod
            def datarequest_exists(cls, title):
                '''Returns true if there is a Data Request with the same title (case insensitive)'''
                query = model.Session.query(cls).autoflush(False)
                return query.filter(func.lower(cls.title) == func.lower(title)).first() is not None

            @classmethod
            def get_ordered_by_date(cls, organization_id=None, user_id=None, closed=None, q=None, desc=False):
                '''Personalized query'''
                query = model.Session.query(cls).autoflush(False)

                params = {}

                if organization_id is not None:
                    params['organization_id'] = organization_id

                if user_id is not None:
                    params['user_id'] = user_id

                if closed is not None:
                    params['closed'] = closed

                if q is not None:
                    search_expr = '%{0}%'.format(q)
                    query = query.filter(or_(cls.title.ilike(search_expr), cls.description.ilike(search_expr)))

                order_by_filter = cls.open_time.desc() if desc else cls.open_time.asc()

                return query.filter_by(**params).order_by(order_by_filter).all()

            @classmethod
            def get_open_datarequests_number(cls):
                '''Returns the number of data requests that are open'''
                return model.Session.query(func.count(cls.id)).filter_by(closed=False).scalar()

        DataRequest = _DataRequest

        # FIXME: References to the other tables...
        datarequests_table = sa.Table('datarequests', model.meta.metadata,
                                      sa.Column('user_id', sa.types.UnicodeText, primary_key=False, default=u''),
                                      sa.Column('id', sa.types.UnicodeText, primary_key=True, default=uuid4),
                                      sa.Column('title', sa.types.Unicode(constants.NAME_MAX_LENGTH), primary_key=True, default=u''),
                                      sa.Column('description', sa.types.Unicode(constants.DESCRIPTION_MAX_LENGTH), primary_key=False, default=u''),
                                      sa.Column('organization_id', sa.types.UnicodeText, primary_key=False, default=None),
                                      sa.Column('open_time', sa.types.DateTime, primary_key=False, default=None),
                                      sa.Column('accepted_dataset_id', sa.types.UnicodeText, primary_key=False, default=None),
                                      sa.Column('close_time', sa.types.DateTime, primary_key=False, default=None),
                                      sa.Column('closed', sa.types.Boolean, primary_key=False, default=False),
                                      sa.Column('close_circumstance', sa.types.Unicode(constants.CLOSE_CIRCUMSTANCE_MAX_LENGTH), primary_key=False, default=u'')
                                      if closing_circumstances_enabled else None,
                                      sa.Column('approx_publishing_date', sa.types.DateTime, primary_key=False, default=None)
                                      if closing_circumstances_enabled else None,
                                      extend_existing=True,
                                      )

        # Create the table only if it does not exist
        datarequests_table.create(checkfirst=True)

        model.meta.mapper(DataRequest, datarequests_table)

        update_db(model)

    if Comment is None:
        class _Comment(model.DomainObject):

            @classmethod
            def get(cls, **kw):
                '''Finds all the instances required.'''
                query = model.Session.query(cls).autoflush(False)
                return query.filter_by(**kw).all()

            @classmethod
            def get_ordered_by_date(cls, datarequest_id, desc=False):
                '''Personalized query'''
                query = model.Session.query(cls).autoflush(False)
                order_by_filter = cls.time.desc() if desc else cls.time.asc()
                return query.filter_by(datarequest_id=datarequest_id).order_by(order_by_filter).all()

            @classmethod
            def get_comment_datarequests_number(cls, **kw):
                '''
                Returned the number of comments of a data request
                '''
                return model.Session.query(func.count(cls.id)).filter_by(**kw).scalar()

        Comment = _Comment

        # FIXME: References to the other tables...
        comments_table = sa.Table('datarequests_comments', model.meta.metadata,
                                  sa.Column('id', sa.types.UnicodeText, primary_key=True, default=uuid4),
                                  sa.Column('user_id', sa.types.UnicodeText, primary_key=False, default=u''),
                                  sa.Column('datarequest_id', sa.types.UnicodeText, primary_key=True, default=uuid4),
                                  sa.Column('time', sa.types.DateTime, primary_key=True, default=u''),
                                  sa.Column('comment', sa.types.Unicode(constants.COMMENT_MAX_LENGTH), primary_key=False, default=u''),
                                  extend_existing=True
                                  )

        # Create the table only if it does not exist
        comments_table.create(checkfirst=True)

        model.meta.mapper(Comment, comments_table,)

    if DataRequestFollower is None:
        class _DataRequestFollower(model.DomainObject):

            @classmethod
            def get(cls, **kw):
                '''Finds all the instances required.'''
                query = model.Session.query(cls).autoflush(False)
                return query.filter_by(**kw).all()

            @classmethod
            def get_datarequest_followers_number(cls, **kw):
                '''
                Returned the number of followers of a data request
                '''
                return model.Session.query(func.count(cls.id)).filter_by(**kw).scalar()

        DataRequestFollower = _DataRequestFollower

        # FIXME: References to the other tables...
        followers_table = sa.Table('datarequests_followers', model.meta.metadata,
                                   sa.Column('id', sa.types.UnicodeText, primary_key=True, default=uuid4),
                                   sa.Column('user_id', sa.types.UnicodeText, primary_key=False, default=u''),
                                   sa.Column('datarequest_id', sa.types.UnicodeText, primary_key=True, default=uuid4),
                                   sa.Column('time', sa.types.DateTime, primary_key=True, default=u''),
                                   extend_existing=True
                                   )

        # Create the table only if it does not exist
        followers_table.create(checkfirst=True)

        model.meta.mapper(DataRequestFollower, followers_table,)


def update_db(model):
    '''
    A place to make any datarequest table updates via SQL commands
    This is required because adding new columns to sqlalchemy metadata will not get created if the table already exists
    '''
    meta = MetaData(bind=model.Session.get_bind(), reflect=True)

    # Check to see if columns exists and create them if they do not exists
    if closing_circumstances_enabled:
        if 'datarequests' in meta.tables:
            if 'close_circumstance' not in meta.tables['datarequests'].columns:
                log.info("DataRequests-UpdateDB: 'close_circumstance' field does not exist, adding...")
                DDL('ALTER TABLE "datarequests" ADD COLUMN "close_circumstance" varchar({0}) NULL'.format(constants.CLOSE_CIRCUMSTANCE_MAX_LENGTH)).execute(model.Session.get_bind())

            if 'approx_publishing_date' not in meta.tables['datarequests'].columns:
                log.info("DataRequests-UpdateDB: 'approx_publishing_date' field does not exist, adding...")
                DDL('ALTER TABLE "datarequests" ADD COLUMN "approx_publishing_date" timestamp NULL').execute(model.Session.get_bind())
