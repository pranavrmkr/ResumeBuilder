"""Navigation helpers for the three-step application workflow tests."""
def navigate(app, section):
    ai_tools = {'Improve entire resume':'Improve entire resume', 'Review & Match':'Review & Match', 'Summary assistant':'Professional Summary', 'Rewrite a field':'Rewrite a field'}
    step = 'AI' if section in ai_tools else 'Preview & export' if section in ('Preview','Preview & export') else 'Edit resume'
    app.sidebar.button(key={'Edit resume':'nav_edit','AI':'nav_ai','Preview & export':'nav_preview'}[step]).click().run()
    if step == 'Edit resume':
        app.sidebar.selectbox(key='editor_section').select(section).run()
    elif step == 'AI':
        app.selectbox(key='studio_tool').select(ai_tools[section]).run()
    return app


def open_summary_rewrite(app):
    navigate(app, 'Rewrite a field')
    app.selectbox(key='studio_section').select('personal_info').run()
    app.selectbox(key='studio_field_personal_info').select('summary').run()
    return app
