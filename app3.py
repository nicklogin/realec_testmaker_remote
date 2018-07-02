from flask import Flask, render_template, url_for, request, send_file, redirect, jsonify
import realec_grammar_exercisesXI
import html
import urllib.parse
import pathlib
##здесь присылаем файл из оперативной памяти:
app = Flask(__name__)

@app.route('/')
def display_index():
    if request.args:
        # print(request.args['essaypath'])
        essay_addr = request.args['essaypath']
        if 'two-variants'in request.args:
            two_var = True
        else:
            two_var = False
        if 'not-repeat' in request.args:
            norepeat = True
        else:
            norepeat = False
        if 'context' in request.args:
            context = True
        else:
            context = False
        files_to_send = realec_grammar_exercisesXI.generate_exercises_from_essay(essay_addr,
        file_output = False, write_txt = False, make_two_variants=two_var, exclude_repeated=norepeat,
        context = context)
        file_to_send = files_to_send['short_answer_xml']
        file_to_send.seek(0)
        return send_file(file_to_send,attachment_filename='short_answer.xml',
        as_attachment = True)
    return render_template('index2.html')

@app.route('/getfile')
def send_exercise_file():
    if request.args:
        essay_addr = html.unescape(request.args['name'])
        essay_addr = str(pathlib.Path(essay_addr).absolute())
        essay_addr += '.xml'
        return send_file(essay_addr)

##Генерируем файл и отправляем ссылку на него
@app.route('/writefile')
def write_on_server():
    if request.args:
        essay_addr = request.args['essaypath']
        essay_addr = html.unescape(essay_addr)
        if request.args['two-variants'] == 'true':
            two_var = True
        else:
            two_var = False
        if request.args['not-repeat'] == 'true':
            norepeat = True
        else:
            norepeat = False
        if request.args['context'] == 'true':
            context = True
        else:
            context = False
        print(essay_addr)
        files_to_send = realec_grammar_exercisesXI.generate_exercises_from_essay(essay_addr, context = context, output_path = './quizzes',
        file_output = True, write_txt = False, make_two_variants = two_var, exclude_repeated = norepeat, hier_choice = True)
        files_to_send = {i:"/getfile?name="+urllib.parse.quote(files_to_send[i],safe='') for i in files_to_send}
        # files_to_send = {i:"https://new-realec-testmaker.herokuapp.com//getfile?name="+urllib.parse.quote(files_to_send[i],safe='') for i in files_to_send}
        return jsonify(files_to_send)

if __name__ == '__main__':
    app.run()
