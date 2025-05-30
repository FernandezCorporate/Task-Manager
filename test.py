from flask import Flask, request, render_template, redirect, jsonify
from flask_sqlalchemy import SQLAlchemy
from flasgger import Swagger

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ctm.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True

db = SQLAlchemy(app)
swagger = Swagger(app)


class Projects(db.Model):
    project_id = db.Column(db.Integer, primary_key=True)
    project_name = db.Column(db.String(20))
    active = db.Column(db.Boolean)

    def __init__(self, project, active):
        self.project_name = project
        self.active = active


class Tasks(db.Model):
    task_id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.project_id'))
    task = db.Column(db.Text)
    status = db.Column(db.Boolean, default=False)

    def __init__(self, project_id, task, status=True):
        self.project_id = project_id
        self.task = task
        self.status = status


with app.app_context():
    db.create_all()


@app.route('/')
def index():
    active = None
    projects = Projects.query.all()
    tasks = Tasks.query.all()

    if len(projects) == 1:
        projects[0].active = True
        active = projects[0].project_id
        db.session.commit()

    if projects:
        for project in projects:
            if project.active:
                active = project.project_id
        if not active:
            projects[0].active = True
            active = projects[0].project_id
    else:
        projects = None

    return render_template('index.html', tasks=tasks, projects=projects, active=active)


@app.route('/add', methods=['POST'])
def add_task():
    found = False
    project_id = None
    task = request.form['task']
    project = request.form['project']
    
    if not task:
        return redirect('/')

    if not project:
        project = 'Tasks'

    projects = Projects.query.all()

    for proj in projects:
        if proj.project_name == project:
            found = True

    if not found:
        add_project = Projects(project, True)
        db.session.add(add_project)
        db.session.commit()
        projects = Projects.query.all()

    for proj in projects:
        if proj.project_name == project:
            project_id = proj.project_id
            proj.active = True
        else:
            proj.active = False

    status = bool(int(request.form['status']))
    new_task = Tasks(project_id, task, status)
    db.session.add(new_task)
    db.session.commit()
    return redirect('/')


@app.route('/close/<int:task_id>')
def close_task(task_id):
    task = Tasks.query.get(task_id)
    if not task:
        return redirect('/')
    task.status = not task.status
    db.session.commit()
    return redirect('/')


@app.route('/delete/<int:task_id>')
def delete_task(task_id):
    task = Tasks.query.get(task_id)
    if not task:
        return redirect('/')
    db.session.delete(task)
    db.session.commit()
    return redirect('/')


@app.route('/clear/<delete_id>')
def clear_all(delete_id):
    Tasks.query.filter(Tasks.project_id == delete_id).delete()
    Projects.query.filter(Projects.project_id == delete_id).delete()
    db.session.commit()
    return redirect('/')


@app.route('/remove/<lists_id>')
def remove_all(lists_id):
    Tasks.query.filter(Tasks.project_id == lists_id).delete()
    db.session.commit()
    return redirect('/')


@app.route('/project/<tab>')
def tab_nav(tab):
    projects = Projects.query.all()
    for project in projects:
        project.active = (project.project_name == tab)
    db.session.commit()
    return redirect('/')


# ✅ REST API WITH SWAGGER DOCS BELOW

@app.route('/api/projects', methods=['GET'])
def api_get_projects():
    """
    Get all projects
    ---
    tags: [Projects]
    responses:
      200:
        description: List of all projects
        schema:
          type: array
          items:
            properties:
              id:
                type: integer
              name:
                type: string
              active:
                type: boolean
    """
    projects = Projects.query.all()
    return jsonify([{'id': p.project_id, 'name': p.project_name, 'active': p.active} for p in projects])


@app.route('/api/projects/<int:id>', methods=['GET'])
def api_get_project(id):
    """
    Get project by ID
    ---
    tags: [Projects]
    parameters:
      - name: id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Project found
      404:
        description: Project not found
    """
    project = Projects.query.get(id)
    if not project:
        return jsonify({'error': 'Project not found'}), 404
    return jsonify({'id': project.project_id, 'name': project.project_name, 'active': project.active})


@app.route('/api/tasks', methods=['GET'])
def api_get_tasks():
    """
    Get all tasks
    ---
    tags: [Tasks]
    responses:
      200:
        description: List of all tasks
    """
    tasks = Tasks.query.all()
    return jsonify([{'id': t.task_id, 'project_id': t.project_id, 'task': t.task, 'status': t.status} for t in tasks])


@app.route('/api/tasks/<int:id>', methods=['GET'])
def api_get_task(id):
    """
    Get task by ID
    ---
    tags: [Tasks]
    parameters:
      - name: id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Task found
      404:
        description: Task not found
    """
    task = Tasks.query.get(id)
    if not task:
        return jsonify({'error': 'Task not found'}), 404
    return jsonify({'id': task.task_id, 'project_id': task.project_id, 'task': task.task, 'status': task.status})


@app.route('/api/projects', methods=['POST'])
def api_create_project():
    """
    Create a new project
    ---
    tags: [Projects]
    parameters:
      - in: body
        name: project
        required: true
        schema:
          type: object
          properties:
            name:
              type: string
            active:
              type: boolean
    responses:
      201:
        description: Project created
    """
    data = request.get_json()
    if not data or 'name' not in data:
        return jsonify({'error': 'Project name is required'}), 400
    project = Projects(data['name'], data.get('active', False))
    db.session.add(project)
    db.session.commit()
    return jsonify({'message': 'Project created', 'id': project.project_id}), 201


@app.route('/api/tasks', methods=['POST'])
def api_create_task():
    """
    Create a new task
    ---
    tags: [Tasks]
    parameters:
      - in: body
        name: task
        required: true
        schema:
          type: object
          properties:
            project_id:
              type: integer
            task:
              type: string
            status:
              type: boolean
    responses:
      201:
        description: Task created
    """
    data = request.get_json()
    if not data or 'task' not in data or 'project_id' not in data:
        return jsonify({'error': 'Missing task or project_id'}), 400
    task = Tasks(data['project_id'], data['task'], data.get('status', True))
    db.session.add(task)
    db.session.commit()
    return jsonify({'message': 'Task created', 'id': task.task_id}), 201


@app.route('/api/projects/<int:id>', methods=['PUT'])
def api_update_project(id):
    """
    Update a project
    ---
    tags: [Projects]
    parameters:
      - name: id
        in: path
        type: integer
        required: true
      - in: body
        name: project
        required: true
        schema:
          type: object
          properties:
            name:
              type: string
            active:
              type: boolean
    responses:
      200:
        description: Project updated
    """
    data = request.get_json()
    project = Projects.query.get(id)
    if not project:
        return jsonify({'error': 'Project not found'}), 404
    project.project_name = data.get('name', project.project_name)
    project.active = data.get('active', project.active)
    db.session.commit()
    return jsonify({'message': 'Project updated'})


@app.route('/api/tasks/<int:id>', methods=['PUT'])
def api_update_task(id):
    """
    Update a task
    ---
    tags: [Tasks]
    parameters:
      - name: id
        in: path
        type: integer
        required: true
      - in: body
        name: task
        required: true
        schema:
          type: object
          properties:
            task:
              type: string
            status:
              type: boolean
    responses:
      200:
        description: Task updated
    """
    data = request.get_json()
    task = Tasks.query.get(id)
    if not task:
        return jsonify({'error': 'Task not found'}), 404
    task.task = data.get('task', task.task)
    task.status = data.get('status', task.status)
    db.session.commit()
    return jsonify({'message': 'Task updated'})


@app.route('/api/projects/<int:id>', methods=['DELETE'])
def api_delete_project(id):
    """
    Delete a project
    ---
    tags: [Projects]
    parameters:
      - name: id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Project deleted
      404:
        description: Project not found
    """
    project = Projects.query.get(id)
    if not project:
        return jsonify({'error': 'Project not found'}), 404
    db.session.delete(project)
    db.session.commit()
    return jsonify({'message': 'Project deleted'})


@app.route('/api/tasks/<int:id>', methods=['DELETE'])
def api_delete_task(id):
    """
    Delete a task
    ---
    tags: [Tasks]
    parameters:
      - name: id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Task deleted
      404:
        description: Task not found
    """
    task = Tasks.query.get(id)
    if not task:
        return jsonify({'error': 'Task not found'}), 404
    db.session.delete(task)
    db.session.commit()
    return jsonify({'message': 'Task deleted'})


@app.route('/api/delete_all', methods=['DELETE'])
def api_delete_all():
    """
    Delete all tasks and projects
    ---
    tags: [Admin]
    responses:
      200:
        description: All records deleted
      500:
        description: Deletion failed
    """
    try:
        Tasks.query.delete()
        Projects.query.delete()
        db.session.commit()
        return jsonify({'message': 'All projects and tasks deleted'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to delete all records', 'details': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
