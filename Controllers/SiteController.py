from application import app, db
from flask import request, jsonify, session
from flask_restful import Resource
from Models.Site import Site
from Models.Revision import Revision
from Controllers.AuthController import login_required


class SiteController(Resource):

    @staticmethod
    @app.route('/api/sites', methods=['POST'])
    @login_required
    def create_site():
        data = request.get_json()
        name = data.get('name', '').strip()
        domain = data.get('domain', '').strip().lower()

        if not name or not domain:
            return jsonify({'message': 'Название и домен обязательны'}), 400

        existing = Site.query.filter_by(domain=domain, user_id=session['user_id']).first()
        if existing:
            return jsonify({'message': 'Сайт с таким доменом уже добавлен'}), 400

        site = Site(
            name=name,
            domain=domain,
            user_id=session['user_id'],
            site_key=Site.generate_site_key()
        )
        db.session.add(site)
        db.session.commit()

        return jsonify({
            'id': str(site.id),
            'name': site.name,
            'domain': site.domain,
            'site_key': site.site_key
        }), 201

    @staticmethod
    @app.route('/api/sites/<site_id>/revisions', methods=['GET'])
    @login_required
    def get_revisions(site_id):
        site = Site.query.filter_by(id=site_id, user_id=session['user_id']).first()
        if not site:
            return jsonify({'message': 'Сайт не найден'}), 404

        revisions = Revision.query.filter_by(site_id=site_id).order_by(Revision.created_at.desc()).all()
        return jsonify([{
            'id': str(r.id),
            'name': r.name,
            'description': r.description,
            'created_at': r.created_at.isoformat(),
            'ended_at': r.ended_at.isoformat() if r.ended_at else None,
            'is_active': r.is_active
        } for r in revisions])

    @staticmethod
    @app.route('/api/sites/<site_id>/revisions', methods=['POST'])
    @login_required
    def create_revision(site_id):
        site = Site.query.filter_by(id=site_id, user_id=session['user_id']).first()
        if not site:
            return jsonify({'message': 'Сайт не найден'}), 404

        data = request.get_json()
        name = data.get('name', '').strip()
        if not name:
            return jsonify({'message': 'Название ревизии обязательно'}), 400

        # Deactivate current active revision
        from datetime import datetime
        active = Revision.query.filter_by(site_id=site_id, is_active=True).first()
        if active:
            active.is_active = False
            active.ended_at = datetime.utcnow()

        revision = Revision(
            site_id=site_id,
            name=name,
            description=data.get('description', '').strip()
        )
        db.session.add(revision)
        db.session.commit()

        return jsonify({
            'id': str(revision.id),
            'name': revision.name,
            'is_active': revision.is_active
        }), 201
