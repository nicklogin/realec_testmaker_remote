from flask import Flask, render_template, url_for, request, send_file, redirect, jsonify
import realec_grammar_exercisesXI
import html
import urllib.parse
import os, inspect
# import pathlib
        
app = Flask(__name__)

@app.route('/')
def display_index():
    #разобраться, почемц перестала работать отправка файла
    #(скорее всего превышение таймаута в 500 мс)
    #можно переделать через javascript, направляя запросы не к главной, а к другой странице сайта
    # if request.args:
    #     # print(request.args['essaypath'])
    #     essay_addr = request.args['essaypath']
    #     if 'two-variants'in request.args:
    #         two_var = True
    #     else:
    #         two_var = False
    #     if 'not-repeat' in request.args:
    #         norepeat = True
    #     else:
    #         norepeat = False
    #     if 'context' in request.args:
    #         context = True
    #     else:
    #         context = False
    #     files_to_send = realec_grammar_exercisesXI.generate_exercises_from_essay(essay_addr,
    #     file_output = False, write_txt = False, make_two_variants=two_var, exclude_repeated=norepeat,
    #     context = context)
    #     if 'short_answer_xml' in files_to_send:
    #         file_to_send = files_to_send['short_answer_xml']
    #     else:
    #         file_to_send = files_to_send['short_answer_variant1_xml']
    #     file_to_send.seek(0)
    #     return send_file(file_to_send,attachment_filename='short_answer.xml',
    #     as_attachment = True)
    #     # for key in files_to_send:
    #     #     file_to_send = files_to_send[key]
    #     #     file_to_send.seek(0)
    #     #     return send_file(file_to_send,attachment_filename=key+'.xml',
    #     #     as_attachment = True)
    return render_template('index3.html')

@app.route('/getfile')
def send_exercise_file():
    if request.args:
        essay_addr = html.unescape(request.args['name'])
        # essay_addr = str(pathlib.Path(essay_addr).absolute())
        prefix = os.path.abspath(os.path.split(inspect.getsourcefile(realec_grammar_exercisesXI))[0]) + '/'
        essay_addr = prefix + essay_addr
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
        prefix = os.path.abspath(os.path.split(inspect.getsourcefile(realec_grammar_exercisesXI))[0])
        # prefix = '/home/nlogin/testmaker_web/realec_testmaker_web'
        prefix += '/'
        # print(essay_addr)
        try:
            files_to_send = realec_grammar_exercisesXI.generate_exercises_from_essay(essay_addr, context = context, output_path = 'quizzes',
            file_output = True, write_txt = False, make_two_variants = two_var, exclude_repeated = norepeat, hier_choice = True,
            include_smaller_mistakes = False, file_prefix = prefix)
        except Exception as e:
            exception = {"doc": e.__doc__ }
            response = jsonify(exception)
            response.status_code = 500
            return response
        # files_to_send = {i:"/getfile?name="+urllib.parse.quote(files_to_send[i],safe='') for i in files_to_send}
        files_to_send = {i:files_to_send[i][len(prefix):] for i in files_to_send}
        files_to_send = {i:"/getfile?name="+urllib.parse.quote(files_to_send[i],safe='') for i in files_to_send}
        # print(files_to_send)
        return jsonify(files_to_send)

if __name__ == '__main__':
    app.run()
