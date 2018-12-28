from app import app, mail, blog_engine
from app.models import User
from flask import render_template
from flask_blogging_patron.signals import page_by_id_fetched,\
        page_by_id_processed
from flask_mail import Message
import logging
from threading import Thread


def send_async_email(app, msg):
    with app.app_context():
        mail.send(msg)


def send_async_bulkmail(app, msg, users):
    with app.app_context():
        try:
            with mail.connect() as conn:
                for user in users:
                    msg.recipients = [user.email]
                    conn.send(msg)
        except Exception as e:
            logging.exception('Exception in send_async_bulkmail')
            raise


def send_email(subject, sender, recipients, text_body, html_body):
    msg = Message(subject, sender=sender, recipients=recipients)
    msg.body = text_body
    msg.html = html_body
    Thread(target=send_async_email, args=(app, msg)).start()


def send_bulkmail(subject, sender, users, text_body, html_body):
    msg = Message(subject, sender=sender)
    msg.body = text_body
    msg.html = html_body
    Thread(target=send_async_bulkmail, args=(app, msg, users)).start()


def send_password_reset_email(user):
    token = user.get_reset_password_token()
    send_email(
        'Password Reset',
        sender=app.config['ADMIN'],
        recipients=[user.email],
        text_body=render_template('email/reset_password.txt',
                                  user=user, token=token),
        html_body=None
    )


def email_post(pid):
    try:
        # run through post processor
        # send processed post to an html template
        # email the html template
        post = blog_engine.storage.get_post_by_id(pid)
        meta = {}
        meta['is_user_blogger'] = False
        meta['post_id'] = pid
        page_by_id_fetched.send(
            blog_engine.app,
            engine=blog_engine,
            post=post,
            meta=meta
        )
        blog_engine.process_post(post, render=True)
        page_by_id_processed.send(
            blog_engine.app,
            engine=blog_engine,
            post=post,
            meta=meta
        )
        html_body = render_template(
            'email/email_post.html',
            post=post,
        )
        text_body = render_template(
            'email/email_post.txt',
            post=post,
        )
        site = app.config.get('BLOGGING_SITENAME')
        users = User.query.filter_by(mail_opt_out=False).all()
        send_bulkmail(
            f'New Update from {site}',
            sender=app.config.get('ADMIN'),
            users=users,
            html_body=html_body,
            text_body=text_body
        )
    except Exception as e:
        logging.exception('Exception in email_post')
        raise
