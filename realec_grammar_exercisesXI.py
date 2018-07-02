import sys, codecs, re, os, traceback
from collections import defaultdict, OrderedDict
import shutil
import random
import json, csv
import pprint
import difflib
#import verb_forms_finder as vff
#import simple_phrase_parser as spp
import time
import realec_helper
import io
##try:
##    import nltk.tag.stanford as stag
##except:
##    pass
##    

"""Script that generates grammar exercises from REALEC data 
grammar tags:
	Punctuation
	Spelling
	Capitalisation
	Grammar
		Determiners
			Articles
				Art_choice
				Art_form
			Det_choice
			Det_form
		Quantifiers
			Quant_choice
			Quant_form
		Verbs
			Tense
				Tense_choice
					Seq_of_tenses
					Choice_in_cond
				Tense_form
					Neg_form
					Form_in_cond
			Voice
				Voice_choice
				Voice_form
			Modals
				Modals_choice
				Modals_form
			Verb_pattern
				Intransitive
				Transitive
					Reflexive_verb
					Presentation
				Ambitransitive
				Two_in_a_row
					Verb_Inf
						Verb_object_inf
						Verb_if
					Verb_Gerund
						Verb_prep_Gerund
							Verb_obj_prep_Gerund
					Verb_Inf_Gerund
						No_diff
						Diff
					Verb_Bare_Inf
						Verb_object_bare
						Restoration_alter
					Verb_part
						Get_part
					Complex_obj
					Verbal_idiom
				Prepositional_verb
					Trans_phrasal
					Trans_prep
					Double_object
					Double_prep_phrasal
				Dative
				Followed_by_a_clause
					that_clause
					if_whether_clause
					that_subj_clause
					it_conj_clause
			Participial_constr
			Infinitive_constr
			Gerund_phrase
			Verb_adj
			Verb_adv
		Nouns
			Countable_uncountable
			Prepositional_noun
			Possessive
			Noun_attribute
			Noun_inf
			Noun_number
				Collective
					Adj_as_collective
		Prepositions
		Conjunctions
			And_syn
			Contrast
			Concession
			Causation
		Adjectives
			Comparative_adj
			Superlative_adj
			Prepositional_adjective
			Adjective_inf
			Adjective_ger
		Adverbs
			Comparative_adv
			Superlative_adv
			Prepositional_adv
			Modifier
		Numerals
			Num_choice
			Num_form
		Pronouns
			Personal
			Reflexive
			Demonstrative
		Agreement_errors
			Animacy
			Number
			Person
		Word_order
			Standard
			Emphatic
			Cleft
			Interrogative
		Abs_comp_clause
			Exclamation
			Title_structure
			Note_structure
		Conditionals
			Cond_choice
			Cond_form
		Attributes
			Relative_clause
				Defining
				Non_defining
				Coordinate
			Attr_participial
		Lack_par_constr
		Negation
		Comparative_constr
			Numerical
		Confusion_of_structures
	Vocabulary
		Word_choice
			lex_item_choice
				Often_confused
			Choice_synonyms
			lex_part_choice
				Absence_comp_colloc
				Redundant
		Derivation
			Conversion
			Formational_affixes
				Suffix
				Prefix
			Category_confusion
			Compound_word
	Discourse
		Ref_device
			Lack_of_ref_device
			Dangling_ref
			Redundant_ref
			Choice_of_ref
		Coherence
			Incoherent_articles
			Incoherent_tenses
				Incoherent_in_cond
			Incoherent_pron
			Linking_device
				Incoherent_conj
				Incoherent_intro_unit
				Lack_of_connective
		Inappropriate_register
		Absence_comp_sent
		Redundant_comp
		Tautology
		Absence_explanation
"""

class Exercise:
    def __init__(self, path_to_realecdata = None, exercise_types = None, output_path = None,
     ann = None, text = None, error_types = [], bold = False, context = False, mode = 'folder',
      maintain_log = True, show_messages = True, use_ram=False,output_file_names = None,
      file_output = True, write_txt = False, keep_processed = False, hier_choice = False,
      make_two_variants = False, exclude_repeated = False):

        """"
        :param error_types: list of str, can include values from
        'Tense_choice', 'Tense_form', 'Voice_choice', 'Voice_form', 'Number', e.g.
        :param exercise_types: list of str, any from: 'multiple_choice', 'word_form', 'short_answer', 'open_cloze'
        :param bold: bool, whether to write error region in bold text
        :param context: bool, whether to include contexts (one sentence before and
        one sentence after) for sentences in exercises
        :param show_messages: bool, whether to display messages in console while generating exercises
        :param write_txt: whether to include plain text representation of exercises in the output along
        with Moodle XML files or ByteIO objects
        :param use_ram: bool
        :param mode: str
        :param path_to_realecdata: str, path to directory with .txt and .ann files if mode == 'folder'
        alternatively path to an .ann file if mode == 'file'
        :param file_output: bool
        :param output_file_names: list of str
        """

        self.exercise_types = exercise_types
        self.error_type = error_types
        self.keep_processed = keep_processed
        # print(self.error_type)
        self.hier_choice = hier_choice
        if self.hier_choice:
            with open ('hierarchy.json','r',encoding='utf-8') as inp:
                self.hierarchy = json.load(inp)
            self.get_hierarchy = lambda x: self.hierarchy[x] if x in self.hierarchy else 0
            self.hier_sort = lambda x: sorted(x,key = self.get_hierarchy, reverse = True)
        self.make_two_variants = make_two_variants
        self.exclude_repeated = exclude_repeated
        # self.sent_tokenize_processed = lambda x: re.findall(r".*?\*\*[0-9]+\*\*.*?[\.?!]",x)
        self.to_include = lambda x: True if (x["Error"] in self.error_type or self.error_type==[''] or not self.error_type) and (x["Relation"]!="Dependant_change") else False
        self.current_doc_errors = OrderedDict()
        self.bold = bold
        self.context = context
        self.write_txt = write_txt
        self.use_ram = use_ram
        self.mode = mode
        self.file_output = file_output
        ##Note: maintain_log is forcibly set to False if file_output is False
        self.maintain_log = maintain_log
        self.show_messages = show_messages
        if self.use_ram:
            self.processed_texts = []
        else:
            self.path_new = './processed_texts/'
        if self.mode == 'direct_input':
            self.ann = ann
            self.text = text
        else:
            self.path_old = path_to_realecdata
        if self.file_output:
            if not output_path:
                output_path = './moodle_exercises'
            os.makedirs(output_path, exist_ok = True)
            self.output_path = output_path
            if output_file_names:
                self.output_file_names = output_file_names
            else:
                self.output_file_names = dict()
                for ex_type in self.exercise_types:
                    if self.make_two_variants and (ex_type=='short_answer' or ex_type=='multiple_choice'):
                        ex_type1 = ex_type+'_variant1'
                        ex_type2 = ex_type+'_variant2'
                        self.output_file_names[ex_type1] = self.output_path+'/{}_{}'.format(''.join([str(i) for i in time.localtime()]),
                                                                                            ex_type1+'_context_'+str(self.context))
                        self.output_file_names[ex_type2] = self.output_path+'/{}_{}'.format(''.join([str(i) for i in time.localtime()]),
                                                                                            ex_type2+'_context_'+str(self.context))
                    else:
                        self.output_file_names[ex_type] = self.output_path+'/{}_{}'.format(''.join([str(i) for i in time.localtime()]),
                                                                                            ex_type+'_context_'+str(self.context))
        else:
            self.maintain_log = False
            self.output_objects = dict()
        if self.maintain_log:
            self.log = []
            self.fieldnames = ["ex_type","text","answers","to_skip","result"]
            self.log_name = '_'.join(self.exercise_types)+'_context='+str(self.context)+'_'+''.join([str(i) for i in time.localtime()])
        self.headword = ''
        self.write_func = {
            "short_answer": self.write_sh_answ_exercise, ##exerciese with selected error region
            "multiple_choice": self.write_multiple_ch, ##exercises with multiple answer selection
            "word_form": self.write_open_cloze, ##exercises where word is to be assigned the appropriate grammar
            "open_cloze": self.write_open_cloze ##exercises where you need to insert something in gap
        }
        # try:
        #     self.tagger = stag.StanfordPOSTagger('english-caseless-left3words-distsim.tagger')
        # except:
        #     self.tagger = False
        if not self.use_ram:
            os.makedirs('./processed_texts', exist_ok=True)
        with open('./wordforms.json', 'r', encoding="utf-8") as dictionary:
            self.wf_dictionary = json.load(dictionary)  # {'headword':[words,words,words]}

    def find_errors_indoc(self, line):
        """
        Find all T... marks and save in dictionary.
        Format: {"T1":{'Error':err, 'Index':(index1, index2), "Wrong":text_mistake}}
        """
        if re.search('^T', line) is not None and 'pos_' not in line:
            try:
                t, span, text_mistake = line.strip().split('\t')
                err, index1, index2 = span.split()
                if err!='note':
                    self.current_doc_errors[t] = {'Error':err, 'Index':(int(index1), int(index2)), "Wrong":text_mistake, "Relation":None}
            except:
                #print (''.join(traceback.format_exception(*sys.exc_info())))
                print("Errors: Something wrong! No notes or a double span", line)

    def validate_answers(self, answer):
        # TO DO: multiple variants?
        if answer.upper() == answer:
            answer = answer.lower()
        answer = answer.strip(r'\'"')
        answer = re.sub(r' ?\(.*?\) ?','',answer)
        if '/' in answer:
            answer = answer.split('/')[0]
        if '\\' in answer:
            answer = answer.split('\\')[0]
        if ' OR ' in answer:
            answer = answer.split(' OR ')[0]
        if ' или ' in answer:
            answer = answer.split(' или ')[0]
        if answer.strip('? ') == '' or '???' in answer:
            return None
        return answer

    def find_answers_indoc(self, line):
        if re.search('^#', line) is not None and 'lemma =' not in line:
            try:
                number, annotation, correction = line.strip().split('\t')
                t_error = annotation.split()[1]
                if self.current_doc_errors.get(t_error):
                    validated = self.validate_answers(correction)
                    if validated is not None:
                        self.current_doc_errors[annotation.split()[1]]['Right'] = validated
            except:
                #print (''.join(traceback.format_exception(*sys.exc_info())))
                print("Answers: Something wrong! No Notes probably", line)

    def find_relations_indoc(self, line):
        if re.search('^R', line) is not None:
            # try:
            number, relation = line.strip().split('\t')
            relation_type, *relation_args = relation.split()
            relation_args = list(map(lambda x: x.split(':')[1], relation_args))
            for arg in relation_args:
                self.current_doc_errors[arg]["Relation"] = relation_type
            # except:
            #     print("Relations: Something wrong! No Notes probably", line)
    
    def find_delete_seqs(self, line):
        if re.search('^A', line) is not None and 'Delete' in line:
            t = line.strip().split('\t')[1].split()[1]
            if self.current_doc_errors.get(t):
                self.current_doc_errors[t]['Delete'] = 'True'

    def make_data_ready_4exercise(self):
        """ Collect errors info """
        print('collecting errors info...')
        if self.mode == 'folder':
            i = 0
            for root, dire, files in os.walk(self.path_old):
                for f in files:
                    i += 1
                    if f.endswith('.ann'):
                        annpath = root+'/'+f
                        self.parse_ann_and_process_text(ann = annpath, processed_text_filename = str(i))
                    
        elif self.mode == 'file':
            self.parse_ann_and_process_text(ann = self.path_old)
        elif self.mode == 'direct_input':
            self.parse_ann_and_process_text()

    def parse_ann_and_process_text(self, ann=None, processed_text_filename = None):
        self.error_intersects = set()
        if self.mode!='direct_input':
            with open(ann, 'r', encoding='utf-8') as ann_file:
                annlines = ann_file.readlines()
        else:
            annlines = self.ann.splitlines()
        for method in (self.find_errors_indoc, self.find_answers_indoc, self.find_relations_indoc, self.find_delete_seqs):
            for line in annlines:
                method(line)
            
        new_errors = OrderedDict()
        for x in sorted(self.current_doc_errors.items(),key=lambda x: (x[1]['Index'][0],x[1]['Index'][1],int(x[0][1:]))):
            if 'Right' in x[1] or 'Delete' in x[1]:
                new_errors[x[0]] = x[1]
        self.current_doc_errors = new_errors
        
        unique_error_ind = []
        error_ind = [self.current_doc_errors[x]['Index'] for x in self.current_doc_errors]
        ##если области ошибки совпадают оставляем те,
        ##которые записаны первыми
        for ind in error_ind:
            if ind in unique_error_ind:
                self.error_intersects.add(ind)
            else:
                unique_error_ind.append(ind)                
        self.embedded,self.overlap1,self.overlap2 = self.find_embeddings(unique_error_ind)
        if self.use_ram:
            if self.mode == 'file':
                self.add_to_processed_list(filename = ann[:ann.find('.ann')])
            elif self.mode == 'direct_input':
                self.add_to_processed_list()
        else:
            if self.mode == 'folder':
                self.make_one_file(ann[:ann.find('.ann')],processed_text_filename)
            elif self.mode == 'direct_input':
                self.save_processed(self.text, output_filename=self.path_new+'processed')
        self.current_doc_errors.clear()

    def find_embeddings(self,indices):
        ##сортируем исправления - сначала сортируем по возрастанию первого индекса,
        ##потом по убыванию второго индекса:
        indices.sort(key=lambda x: (x[0],-x[1]))
        embedded = []
        overlap1, overlap2 = [],[]
        self.embedding = defaultdict(list)
        for i in range(1,len(indices)):
            find_emb = [x for x in indices if (x[0] <= indices[i][0] and x[1] > indices[i][1]) or \
                                              (x[0] < indices[i][0] and x[1] >= indices[i][1])]
            if find_emb:
                ##в self.embedding для каждой ошибки с большей областью записываем текущую ошибку:
                for j in find_emb:
                    self.embedding[str(j)].append(indices[i])
                ##в self.embedded записываем те ошибки, для которых есть ошибки с большей областью:
                embedded.append(indices[i])
            else:
                overlaps = [x for x in indices if x[0] < indices[i][0] and (x[1] > indices[i][0] and
                                                                            x[1] < indices[i][1])]
                if overlaps:
                    ##самое левое наслаивание по отношению к ошибке уходит в overlap1:
                    overlap1.append(overlaps[0])
                    ##сама ошибка уходит в overlap2:
                    overlap2.append(indices[i])
        ## на выход:
        ## наложения - словарь - индекс начала: индексы концов
        ## пересечения1 и пересечения 2 - аннотации, которые пересекаются, идут отдельно
        return embedded, overlap1, overlap2
        
    def tackle_embeddings(self,dic):
        b = dic.get('Index')[0]
        ##записываем в emb_errors ошибки, область которых меньше данной:
        emb_errors = [x for x in self.current_doc_errors.items() if (x[1]['Index'] in self.embedding[str(dic.get('Index'))]) and ('Right' in x[1])]
        new_wrong = ''
        nw = 0
        ignore = []
        for j,ws in enumerate(dic['Wrong']):
            emb_intersects = []
            for t,e in emb_errors:
                if e['Index'][0]-b == j:
                    if 'Right' in e and 'Right' in dic and e['Right'] == dic['Right']:
                        break
                    if str(e['Index']) in self.embedding:
                        ignore += self.embedding[str(e['Index'])]
                    if e['Index'] in self.error_intersects:
                        emb_intersects.append((int(t[1:]),e))
                        continue
                    if e['Index'] not in ignore:
                        if 'Right' in e:
                            new_wrong += e['Right']
                            nw = len(e['Wrong'])
                        elif 'Delete' in e:
                            nw = len(e['Wrong'])
            if emb_intersects:
                emb_intersects = sorted(emb_intersects,key=lambda x: x[0])
                ##а что если попробовать брать самый важный, а не самый последний поставленный тег для аннотаций, область которых совпадает?
                ##лучше этого не делать, можут аолучиться жуть:
                # emb_intersects = sorted(emb_intersects,key=lambda x: self.get_hierarchy(x[1]['Error']))
                last = emb_intersects[-1][1]
                L = -1
                while 'Right' not in last and abs(L)<len(emb_intersects):
                    L -= 1
                    last = emb_intersects[L][1]
                new_wrong += last['Right']
                nw = len(last['Wrong'])
            if not nw:
                new_wrong += ws
            else:
                nw -= 1
        return new_wrong

    def find_overlap(self,s1,s2):
        m = difflib.SequenceMatcher(None, s1, s2).get_matching_blocks()
        if len(m) > 1:
            for x in m[:-1]:
                if x.b == 0:
                    return x.size
        return 0
            

    def make_one_file(self, filename, new_filename):
        """
        Makes file with current types of errors. all other errors checked.
        :param filename: name of the textfile
        return: nothing. just write files in dir <<processed_texts>>
        """
        with open(filename+'.txt', 'r', encoding='utf-8') as text_file:
            print(filename+'.txt')
            self.save_processed(text_file.read(), output_filename = self.path_new+new_filename+'.txt')
                
    def add_to_processed_list(self, filename = None):
        if self.mode != 'direct_input':
            with open(filename+'.txt', 'r', encoding='utf-8') as text_file:
                self.processed_texts.append(self.save_processed(text_file.read(), output_filename=filename))
        else:
            self.processed_texts.append(self.save_processed(self.text))

    def save_processed(self, one_text, output_filename = None):
        processed = ''
        not_to_write_sym = 0
        for i, sym in enumerate(one_text):
            ##идём по каждому символу оригинального текста эссе:
            intersects = []
            ##перебираем все ошибки в этом эссе
            for t_key, dic in self.current_doc_errors.items():
                ##если начало какой-либо ошибки приходится на текущий символ:
                if dic.get('Index')[0] == i:
                    if (dic.get('Error') == 'Punctuation' or dic.get('Error') == 'Defining') and 'Right' in dic and \
                       not dic.get('Right').startswith(','):
                        dic['Right'] = ' '+dic['Right']
                    ##если исправление попало в меньшую область ошибки - не берём его:
                    if dic.get('Index') in self.embedded:
                        continue
                    ##если исправление попало в большую (закрывающую) область ошибки - берём:
                    if str(dic.get('Index')) in self.embedding:
                        if self.to_include(dic):
                            new_wrong = self.tackle_embeddings(dic)
                            processed += '**'+str(dic.get('Right'))+'**'+str(dic.get('Error'))+'**'+str(dic.get('Relation'))+'**'+str(len(new_wrong))+'**'+new_wrong
                            ##устанавливаем, сколько итераций мы не будем дописывать символы:
                            not_to_write_sym = len(dic['Wrong'])
                            break

                    ##если среди пересечений, которые идут раньше
                    if dic.get('Index') in self.overlap1:
                        if not self.to_include(dic):
                            overlap2_ind = self.overlap2[self.overlap1.index(dic.get('Index'))]
                            overlap2_err = [x for x in self.current_doc_errors.values() if x['Index'] == overlap2_ind][-1]
                            if 'Right' in dic and 'Right' in overlap2_err:
                                ##находим число совпадающих элементов в пересекающихся ошибках:
                                rn = self.find_overlap(dic['Right'],overlap2_err['Right'])
                                ##разница правой границы первого и левой границы второго:
                                wn = dic['Index'][1] - overlap2_err['Index'][0]
                                ##разница между длиной первого и предыдущей разницей:
                                indexes_comp = dic.get('Index')[1] - dic.get('Index')[0] - wn
                                if rn == 0:
                                    processed += str(dic.get('Right'))+'#'+str(indexes_comp)+'#'+str(dic.get('Wrong'))[:-wn]
                                else:
                                    processed += str(dic.get('Right')[:-rn])+'#'+str(indexes_comp)+'#'+str(dic.get('Wrong'))[:-wn]
                                not_to_write_sym = len(str(dic.get('Wrong'))) - wn
                                break

                    ##если среди пересечений, которые идут позже:
                    if dic.get('Index') in self.overlap2:
                        overlap1_ind = self.overlap1[self.overlap2.index(dic.get('Index'))]
                        overlap1_err = [x for x in self.current_doc_errors.values() if x['Index'] == overlap1_ind][-1]
                        if self.to_include(overlap1_err):
                            if not self.to_include(dic):
                                if 'Right' in dic and 'Right' in overlap1_err:
                                    rn = self.find_overlap(overlap1_err['Right'],dic['Right'])
                                    ##разница правой границы первого и левой границы второго
                                    wn = overlap1_err['Index'][1] - dic['Index'][0]
                                    indexes_comp = dic.get('Index')[1] - dic.get('Index')[0] - wn
                                    processed += dic.get('Wrong')[:wn] + dic.get('Right')[rn:] +'#'+str(indexes_comp)+ '#'+dic.get('Wrong')[wn:]
                                    not_to_write_sym = len(str(dic.get('Wrong')))
                            break
                            
                            
                    if dic.get('Index') in self.error_intersects:
                        intersects.append((int(t_key[1:]),dic))
                        continue

                    if dic.get('Right'):
                        indexes_comp = dic.get('Index')[1] - dic.get('Index')[0]
                        if self.to_include(dic):
                            processed += '**'+str(dic.get('Right'))+'**'+str(dic.get('Error'))+'**'+str(dic.get('Relation'))+'**'+str(indexes_comp)+'**'
                        else:
                            processed += dic.get('Right') +'#'+str(indexes_comp)+ '#'
                    else:
                        if dic.get('Delete'):
                            indexes_comp = dic.get('Index')[1] - dic.get('Index')[0]
                            processed += "#DELETE#"+str(indexes_comp)+"#"
                            
            if intersects:
                intersects = sorted(intersects,key=lambda x: x[0])
                intersects = [x[1] for x in intersects]
                needed_error_types = [x for x in intersects if self.to_include(x)]
                if needed_error_types and 'Right' in needed_error_types[-1]:
                    ## из входящих друг в друга тегов берётся самый верхний:
                    saving = needed_error_types[-1]
                    intersects.remove(saving)
                    if intersects:
                        to_change = intersects[-1]
                        if 'Right' not in to_change or to_change['Right'] == saving['Right']:
                            indexes_comp = saving['Index'][1] - saving['Index'][0]
                            processed += '**'+str(saving['Right'])+'**'+str(saving['Error'])+'**'+str(saving['Relation'])+'**'+str(indexes_comp)+'**'
                        else: 
                            indexes_comp = len(to_change['Right'])
                            not_to_write_sym = saving['Index'][1] - saving['Index'][0]
                            processed += '**'+str(saving['Right'])+'**'+str(saving['Error'])+'**'+str(saving['Relation'])+'**'+str(indexes_comp)+'**'+to_change['Right']
                else:
                    if 'Right' in intersects[-1]:
                        if len(intersects) > 1 and 'Right' in intersects[-2]:
                            indexes_comp = len(intersects[-2]['Right'])
                            not_to_write_sym = intersects[-1]['Index'][1] - intersects[-1]['Index'][0]
                            processed += intersects[-1]['Right'] + '#'+str(indexes_comp)+ '#' + intersects[-2]['Right']
                        else:
                            indexes_comp = intersects[-1]['Index'][1] - intersects[-1]['Index'][0]
                            processed += intersects[-1]['Right'] + '#'+str(indexes_comp)+ '#'
            if not not_to_write_sym:
                processed += sym
            else:
                not_to_write_sym -= 1
        if not self.use_ram:
            # print('Saving processed text to ', output_filename)
            with open(output_filename+'.txt', 'w', encoding='utf-8') as new_file:
                new_file.write(processed)
        else:
            return processed
        
        
    # ================Write Exercises to the files=================

#     def find_choices(self, right, wrong, new_sent): #TODO @Kate, rewrite this function
#         """
#         Finds two more choices for Multiple Choice exercise.
#         :param right:
#         :param wrong:
#         :return: array of four choices (first is always right)
#         """
#         right = re.sub('[а-яА-ЯЁё].*?[а-яёА-ЯЁ]','',right)
#         wrong = re.sub('[а-яА-ЯЁё].*?[а-яёА-ЯЁ]','',wrong)
#         choices = [right, wrong]
#         if self.error_type == ['Number']:
#             if not self.tagger:
#                 print('''Cannot proceed - NLTK package with Stanford POS Tagger needed to create Multiple choice questions on
# Number''')
#                 raise Exception
#             quantifiers = ('some', 'someone', 'somebody', 'one', 'everyone', 'everybody', 'noone',
#              'no-one', 'nobody', 'something', 'everything', 'nothing')
#             if self.tagger.tag(right.split())[0][1].startswith('V') and self.tagger.tag(wrong.split())[0][1].startswith('V'):
# ##                print('Stanford POS Tagger OK')
#                 quant_presence = False
#                 tagged_sent = self.tagger.tag(new_sent.replace('_______',right).split())
#                 for i in range(len(tagged_sent)):
#                     if tagged_sent[i][0] in quantifiers:
#                         quant_presence = True
#                     if tagged_sent[i][0] == right.split()[0] and tagged_sent[i][1].startswith('V') and quant_presence:
#                         [choices.append(i) for i in (vff.neg(right), vff.neg(wrong))\
#                          if (i!=right) and (i!=wrong) and (i!='') and (i!=None)]
#                         break
#         elif self.error_type == ['Preposotional_noun','Prepositional_adjective','Prepositional_adv', 'Prepositional_verb']:
#             pr1 = spp.find_prep(right)
#             pr2 = spp.find_prep(wrong)
#             if pr1['prep']:
#                 prep, left, rite = pr1['prep'], pr1['left'], pr1['right']
#                 preps = 'at', 'for', 'on'
#                 variants = set(left + i + rite for i in preps)
#                 if ((left + rite).strip(' ') == (pr2['left']+pr2['right']).strip(' ')):
#                     [choices.append(i) for i in variants if i.strip(' ') != right.lower().strip(' ') and i.strip(' ') != wrong.lower().strip(' ')]
#             elif pr2['prep']:
#                 prep, left, rite = pr2['prep'], pr2['left'], pr2['right']
#                 preps = 'at', 'for', 'on'
#                 variants = set(left + i + rite for i in preps)
#                 if left+rite.strip(' ') == pr1['left'].strip(' '):
#                     [choices.append(i) for i in variants if i.strip(' ') != right.lower().strip(' ') and i.strip(' ') != wrong.lower().strip(' ')]
#         elif self.error_type == ['Conjunctions','Absence_comp_sent','Lex_item_choice','Word_choice',
#         'Conjunctions','Lex_part_choice','Often_confused','Absence_comp_colloc','Redundant','Redundant_comp']:
#             conjunctions1 = ['except', 'besides','but for']
#             conjunctions2 = ['even if', 'even though', 'even']
#             if right in conjunctions1:
#                 [choices.append(i) for i in conjunctions1 if (i != right) and (i != wrong)]
#             elif right in conjunctions2:
#                 [choices.append(i) for i in conjunctions2 if (i != right) and (i != wrong)]
#         elif self.error_type == ['Defining']:
#             gerund_form = spp.find_verb_form(right,'gerund')
#             add_forms = vff.find_verb_forms(gerund_form)
#             new_choices = []
#             if gerund_form:
#                 continuous_form = spp.find_anal_form(right,gerund_form)
#                 new_choices.append(right.replace(gerund_form, 'being ' + add_forms['3rd'], 1))
#                 new_choices.append(right.replace(continuous_form, add_forms['2nd'], 1))
#                 if ("n't" in continuous_form) or ('not' in continuous_form):
#                     new_choices = [vff.neg(i) for i in new_choices]
#                 [choices.append(i) for i in new_choices if i != right and i != wrong]
#         elif self.error_type == ['Choice_in_cond','Form_in_cond','Incoherent_in_cond'] and ('would' in right):
#             neg = False
#             if "wouldn't" in right:
#                 neg = True
#             lex_verb = spp.find_verb_form(right[right.find('would'):],'any')
#             if lex_verb.count(' ') == 0:
#                 lex_verb_forms = vff.find_verb_forms(lex_verb)
#                 if lex_verb_forms:
#                     new_choices = set([lex_verb_forms['2nd'], 'would have '+lex_verb_forms['3rd'],'would '+lex_verb_forms['bare_inf']])
#             else:
#                 be_form, verb_form = lex_verb.split(' ')
#                 new_choices = set()
#                 if (be_form == 'are') or (be_form == 'were'):
#                     new_choices.add('were '+verb_form)
#                 else:
#                     new_choices.add('was '+verb_form)
#                 new_choices.add('would have been '+verb_form)
#                 new_choices.add('would be '+verb_form)
#             if neg:
#                 new_choices = [vff.neg(i) for i in new_choices]
#             new_choices = [right[:right.find('would')]+i+right[right.find(lex_verb)+len(lex_verb):] for i in new_choices]
#             [choices.append(i) for i in new_choices if i!=right and i != wrong]
#         return choices[:4]

    

    def check_headform(self, word):
        """Take initial fowm - headform of the word"""
        for key, value in self.wf_dictionary.items():
            headword = [val for val in value if val == word]
            if len(headword)>0:
                return key

    def create_sentence_function(self, new_text):
        """
        Makes sentences and write answers for all exercise types
        :return: array of good sentences. [ (sentences, [right_answer, ... ]), (...)]
        """

        def build_exercise_text(text, answers, index=None):
            # if sent1 and sent3 and self.context: # fixed sentences beginning with a dot
            #     text = correct_all_errors(sent1) + '. ' + new_sent + ' ' + correct_all_errors(sent3) + '.'
            # elif sent3 and self.context:
            #     text = new_sent + ' ' + correct_all_errors(sent3) + '.'
            # else:
            #     text = new_sent
            text = re.sub(' +',' ',text)
            text = re.sub('[а-яА-ЯЁё]+','',text)
            if self.maintain_log:
                question_log = {"ex_type":ex_type,"text":text,"answers":answers,"to_skip":to_skip,"result":"not included"}
            if ('**' not in text) and (not to_skip) and (answers != []):
                ##закомменть:
                if self.show_messages:
                    print('text, answers: ', text, answers)
                if self.maintain_log:
                    question_log["result"] = "ok"
                if not index:
                    good_sentences[ex_type].append((text, answers))
                else:
                    good_sentences[ex_type+'_variant'+str(index)].append((text, answers))
            elif '**' in text:
                if self.show_messages:
                    print('text and answers arent added cause ** in text: ', text, answers)
            elif to_skip:
                if self.show_messages:
                    print('text and answers arent added cause to_skip = True: ', text, answers)
            if self.maintain_log:
                self.log.append(question_log)
        good_sentences = {x:list() for x in self.exercise_types}
        if self.make_two_variants:
            if 'short_answer' in good_sentences:
                good_sentences.pop('short_answer')
                good_sentences['short_answer_variant1'] = list()
                good_sentences['short_answer_variant2'] = list()
            if 'multiple_choice' in good_sentences:
                good_sentences.pop('multiple_choice')
                good_sentences['multiple_choice_variant1'] = list()
                good_sentences['multiple_choice_variant2'] = list()
        types1 = [i for i in self.exercise_types if i!='word_form']
        sentences = new_text.split('.')
        # i = 0
        if self.context:
            sentences = ['.'.join(sentences[i:i+3]) for i in range(0,len(sentences),3)]
            # for sentence in sentences:
            #     print(sentence)
        for sent2 in sentences:
            # i += 1
            to_skip = False
            if '**' in sent2:
                ex_type = random.choice(self.exercise_types)
                try:
                    sent, right_answer, err_type, relation, index, other = sent2.split('**')
                    wrong = other[:int(index)]
                    new_sent, answers = '', []
                    if self.make_two_variants and self.exclude_repeated and (ex_type=='short_answer' or ex_type=='multiple_choice'):
                        continue
                    if ex_type == 'word_form':
                        try:
                            new_sent = sent + "{1:SHORTANSWER:=%s}" % right_answer + ' (' +\
                                   self.check_headform(right_answer) + ')' + other[int(index):] + '.'
                            answers = [right_answer]
                        except:
                            if len(self.exercise_types) > 1:
                                ex_type = random.choice(types1) 
                            else:
                                continue
                    if ex_type == 'short_answer':
                        if self.bold:
                            new_sent = sent + '<b>' + wrong + '</b>' + other[int(index):] + '.'
                        else:
                            new_sent = sent + wrong + other[int(index):] + '.'
                        answers = [right_answer]
                    if ex_type == 'open_cloze':
                        new_sent = sent + "{1:SHORTANSWER:=%s}" % right_answer + other[int(index):] + '.'
                        answers = [right_answer]
                    # if ex_type == 'multiple_choice':
                    #     new_sent = sent + "_______ " + other[int(index):] + '.'
                    #     answers = self.find_choices(right_answer, wrong, new_sent)
                    #     if len(answers)<3:
                    #         sentences[i] = sent + ' ' + right_answer + ' ' + other[int(index):] + '.'
                    #         answers = []
                    #     else:
                    #         if self.show_messages:
                    #             print('choices: ',answers)
                        
                except:
                    ## вот здесь работаем с предложениями, где больше одной ошибки
                    ## сюда имплементируй иерархию тегов:
                    split_sent = sent2.split('**')
                    n = (len(split_sent) - 1) / 5
                    if n%1:
                        print('Some issues with markup, skipping:',sent2)
                        continue
                    new_sent,answers = '',[]
                    if ex_type=='short_answer' or ex_type=='multiple_choice':
                        if not self.hier_choice:
                            chosen = random.randint(0,n-1)
                            if self.make_two_variants:
                                other_err_ids = list(range(0,n))
                                other_err_ids.pop(chosen)
                                chosen2 = random.choice(other_err_ids)
                        else:
                            new_sent2, answers2 = '',[]
                            err_types = list(enumerate([split_sent[i] for i in range(len(split_sent)) if i%6==1])) ##находим все типы ошибок в предложении
                            err_types = sorted(err_types, key = lambda x: self.get_hierarchy(x[1]), reverse = True) ##сортируем порядковые номера (по нахождению в тексте слева направо тегов
                            ##ошибок в согласии с иерархией тегов ошибок)
                            chosen = err_types[0][0]
                            if self.make_two_variants:
                                if split_sent[chosen*5+3]!='Parallel_construction':
                                    chosen2 = err_types[1][0]
                                else:
                                    chosen2 = -1
                                    for i in range(1,len(err_types)):
                                        if split_sent[i*5+3]=='Parallel_construction' and split_sent[i*5+1]==split_sent[chosen*5+1]:
                                            continue
                                        else:
                                            chosen2 = err_types[i][0]
                                    if chosen2 == -1:
                                        if self.exclude_repeated:
                                            continue
                                        else:
                                            chosen2 = err_types[1][0]
                            # print(chosen, chosen2)
                    sent_errors = [{'sent':split_sent[i],'right_answer':split_sent[i+1],'err_type':split_sent[i+2],
                    'relation':split_sent[i+3],'index':split_sent[i+4],'other':split_sent[i+5]} for i in range(0,len(split_sent),5) if len(split_sent[i:i+4]) > 1]
                    # print(chosen, len(sent_errors))
                    for i in range(len(sent_errors)):
                        if not to_skip:
                            # sent, right_answer, err_type, relation, index, other = split_sent[i],split_sent[i+1],split_sent[i+2],split_sent[i+3],split_sent[i+4],split_sent[i+5]
                            sent,right_answer,index,relation,other = sent_errors[i]['sent'],sent_errors[i]['right_answer'],sent_errors[i]['index'],sent_errors[i]['relation'],sent_errors[i]['other']
                            try:
                                index = int(index)
                            except:
                                to_skip = True
                                # print('index: ', index)
                                continue
                            if ex_type == 'open_cloze' or ex_type == 'word_form':
                                if ex_type == 'open_cloze':
                                    new_sent += "{1:SHORTANSWER:=%s}" % right_answer + other[int(index):]
                                elif ex_type == 'word_form':
                                    try:
                                        new_sent += "{1:SHORTANSWER:=%s}" % right_answer + ' (' +\
                                            self.check_headform(right_answer) + ')' + other[int(index):]
                                    except:
                                        new_sent += right_answer + other[int(index):]
                            else:
                                if i == chosen:
                                    wrong = other[:int(index)]
                                    if ex_type == 'short_answer':
                                        if self.bold:
                                            new_sent += '<b>' + wrong + '</b>' + other[int(index):]
                                        else:
                                            new_sent += wrong + other[int(index):]
                                        answers = [right_answer]
                                        # print(right_answer)
                                    if self.make_two_variants:
                                        new_sent2 += right_answer + other[int(index):]
                                    # elif ex_type == 'multiple_choice':
                                    #     new_sent2 += "_______ " + other[int(index):]
                                    #     answers2 = self.find_choices(right_answer, wrong, sent)
                                    #     if len(answers)<3:
                                    #         new_sent2 += right_answer + other[int(index):]
                                    #         answers2 = []
                                elif self.make_two_variants:
                                    if i==chosen2:
                                        wrong = other[:int(index)]
                                        if ex_type == 'short_answer':
                                            if self.bold:
                                                new_sent2 += '<b>' + wrong + '</b>' + other[int(index):]
                                            else:
                                                new_sent2 += wrong + other[int(index):]
                                            answers2 = [right_answer]
                                        # elif ex_type == 'multiple_choice':
                                        #     new_sent2 += "_______ " + other[int(index):]
                                        #     answers = self.find_choices(right_answer, wrong, sent)
                                        #     if len(answers)<3:
                                        #         new_sent += right_answer + other[int(index):]
                                        #         answers = []
                                        new_sent += right_answer + other[int(index):]
                                    else:
                                        new_sent += right_answer + other[int(index):]
                                        if relation == 'Parallel_construction' and right_answer == sent_errors[chosen2]['right_answer']:
                                            if ex_type == 'short_answer':
                                                if self.bold:
                                                    new_sent2 += '<b>' + wrong + '</b>' + other[int(index):]
                                                else:
                                                    new_sent2 += wrong + other[int(index):]
                                            # elif ex_type == 'multiple_choice':
                                            #     new_sent2 += "_______ " + other[int(index):]
                                        else:
                                            new_sent2 += right_answer + other[int(index):]
                                else:
                                    if relation == 'Parallel_construction' and right_answer == sent_errors[chosen]['right_answer']:
                                        if ex_type == 'short_answer':
                                            if self.bold:
                                                new_sent += '<b>' + wrong + '</b>' + other[int(index):]
                                            else:
                                                new_sent += wrong + other[int(index):]
                                        # elif ex_type == 'multiple_choice':
                                        #     new_sent += "_______ " + other[int(index):]
                                    else:
                                        new_sent += right_answer + other[int(index):]
                            if i == 0:
                                new_sent = sent + new_sent
                                if self.make_two_variants:
                                    new_sent2 = sent + new_sent2
                        else:
                            new_sent = new_sent + '.'
                            if self.make_two_variants:
                                new_sent2 = new_sent2 + '.'
                if self.make_two_variants:
                    if ex_type in ('short_answer','multiple_choice'):
                        if sent2.count('**')>5:
                            build_exercise_text(new_sent,answers,1)
                            build_exercise_text(new_sent2,answers2,2)
                        else:
                            build_exercise_text(new_sent,answers,1)
                            build_exercise_text(new_sent,answers,2)
                    else:
                        build_exercise_text(new_sent,answers)
                else:
                    build_exercise_text(new_sent,answers)
        return good_sentences

    def write_sh_answ_exercise(self, sentences, ex_type):
        pattern = '<question type="shortanswer">\n\
                    <name>\n\
                    <text>Grammar realec. Short answer {}</text>\n\
                     </name>\n\
                <questiontext format="html">\n\
                <text><![CDATA[{}]]></text>\n\
             </questiontext>\n\
        <answer fraction="100">\n\
        <text><![CDATA[{}]]></text>\n\
        <feedback><text>Correct!</text></feedback>\n\
        </answer>\n\
        </question>\n'
        if self.file_output:
            with open(self.output_file_names[ex_type]+'.xml', 'w', encoding='utf-8') as moodle_ex:
                moodle_ex.write('<quiz>\n')
                for n, ex in enumerate(sentences):
                    moodle_ex.write((pattern.format(n, ex[0], ex[1][0])).replace('&','and'))
                moodle_ex.write('</quiz>')
            if self.write_txt:
                with open(self.output_file_names[ex_type]+'.txt', 'w', encoding='utf-8') as plain_text:
                    for ex in sentences:
                        plain_text.write(ex[1][0]+'\t'+ex[0]+'\n\n')
        else:
            moodle_ex = io.BytesIO()
            moodle_ex.write('<quiz>\n'.encode('utf-8'))
            for n, ex in enumerate(sentences):
                moodle_ex.write((pattern.format(n, ex[0], ex[1][0])).replace('&','and').encode('utf-8'))
            moodle_ex.write('</quiz>'.encode('utf-8'))
            self.output_objects[ex_type+'_xml'] = moodle_ex
            if self.write_txt:
                plain_text = io.BytesIO()
                for ex in sentences:
                    plain_text.write(ex[1][0]+'\t'+ex[0]+'\n\n'.encode('utf-8'))
                self.output_objects[ex_type+'_txt'] = plain_text

    def write_multiple_ch(self, sentences, ex_type):
        pattern = '<question type="multichoice">\n \
        <name><text>Grammar realec. Multiple Choice question {} </text></name>\n \
        <questiontext format = "html" >\n <text> <![CDATA[ <p> {}<br></p>]]></text>\n</questiontext>\n\
        <defaultgrade>1.0000000</defaultgrade>\n<penalty>0.3333333</penalty>\n\
        <hidden>0</hidden>\n<single>true</single>\n<shuffleanswers>true</shuffleanswers>\n\
        <answernumbering>abc</answernumbering>\n<correctfeedback format="html">\n\
        <text>Your answer is correct.</text>\n</correctfeedback>\n\
        <partiallycorrectfeedback format="html">\n<text>Your answer is partially correct.</text>\n\
        </partiallycorrectfeedback>\n<incorrectfeedback format="html">\n\
        <text>Your answer is incorrect.</text>\n</incorrectfeedback>\n'
        if self.file_output:
            with open(self.output_file_names[ex_type]+'.xml', 'w', encoding='utf-8') as moodle_ex:
                moodle_ex.write('<quiz>\n')
                for n, ex in enumerate(sentences):
                    moodle_ex.write((pattern.format(n, ex[0])).replace('&','and'))
                    for n, answer in enumerate(ex[1]):
                        correct = 0
                        if n == 0:
                            correct = 100
                        moodle_ex.write('<answer fraction="{}" format="html">\n<text><![CDATA[<p>{}<br></p>]]>'
                                        '</text>\n<feedback format="html">\n</feedback>\n</answer>\n'.format(correct, answer))
                    moodle_ex.write('</question>\n')
                moodle_ex.write('</quiz>')
            if self.write_txt:
                with open(self.output_file_names[ex_type]+'.txt', 'w',encoding='utf-8') as plain_text:
                    for ex in sentences:
                        plain_text.write(ex[0] + '\n' + '\t'.join(ex[1]) + '\n\n')
        else:
            moodle_ex = io.BytesIO()
            moodle_ex.write('<quiz>\n'.encode('utf-8'))
            for n, ex in enumerate(sentences):
                moodle_ex.write((pattern.format(n, ex[0])).replace('&','and').encode('utf-8'))
                for n, answer in enumerate(ex[1]):
                    correct = 0
                    if n == 0:
                        correct = 100
                    moodle_ex.write('<answer fraction="{}" format="html">\n<text><![CDATA[<p>{}<br></p>]]>'
                                    '</text>\n<feedback format="html">\n</feedback>\n</answer>\n'.format(correct,
                                     answer).encode('utf-8'))
                moodle_ex.write('</question>\n'.encode('utf-8'))
            moodle_ex.write('</quiz>'.encode('utf-8'))
            self.output_objects[ex_type+'_xml'] = moodle_ex
            if self.write_txt:
                plain_text = io.BytesIO()
                for ex in sentences:
                    plain_text.write(ex[0] + '\n' + '\t'.join(ex[1]) + '\n\n'.encode('utf-8'))
                self.output_objects[ex_type+'_txt'] = plain_text

    def write_open_cloze(self, sentences, ex_type):
        """:param type: Word form or Open cloze"""
        type = ''
        if ex_type == 'word_form':
            type = "Word form"
        elif ex_type == 'open_cloze':
            type = "Open Cloze"
        pattern = '<question type="cloze"><name><text>Grammar realec. {} {}</text></name>\n\
                     <questiontext format="html"><text><![CDATA[<p>{}</p>]]></text></questiontext>\n''<generalfeedback format="html">\n\
                     <text/></generalfeedback><penalty>0.3333333</penalty>\n\
                     <hidden>0</hidden>\n</question>\n'
        if self.file_output:
            with open(self.output_file_names[ex_type]+'.xml','w', encoding='utf-8') as moodle_ex:
                moodle_ex.write('<quiz>\n')
                for n, ex in enumerate(sentences):
                    moodle_ex.write((pattern.format(type, n, ex[0])).replace('&','and'))
                moodle_ex.write('</quiz>')
            if self.write_txt:
                with open(self.output_file_names[ex_type]+'.txt','w', encoding='utf-8') as plain_text:
                    for ex in sentences:
                        plain_text.write(ex[0]+'\n\n')
        else:
            moodle_ex = io.BytesIO()
            moodle_ex.write('<quiz>\n'.encode('utf-8'))
            for n, ex in enumerate(sentences):
                moodle_ex.write((pattern.format(type, n, ex[0])).replace('&','and').encode('utf-8'))
            moodle_ex.write('</quiz>'.encode('utf-8'))
            self.output_objects[ex_type+'_xml'] = moodle_ex
            if self.write_txt:
                plain_text = io.BytesIO()
                for ex in sentences:
                    plain_text.write(ex[0] + '\n' + '\t'.join(ex[1]) + '\n\n'.encode('utf-8'))
                self.output_objects[ex_type+'_txt'] = plain_text

    def make_exercise(self):
        """Write it all in moodle format and txt format"""
        print('Making exercises...')
        all_sents = {x:list() for x in self.exercise_types}
        if self.make_two_variants:
            if 'short_answer' in all_sents:
                all_sents.pop('short_answer')
                all_sents['short_answer_variant1'] = list()
                all_sents['short_answer_variant2'] = list()
            if 'multiple_choice' in all_sents:
                all_sents.pop('multiple_choice')
                all_sents['multiple_choice_variant1'] = list()
                all_sents['multiple_choice_variant2'] = list()
        if self.use_ram:
            list_to_iter = self.processed_texts
        else:
            list_to_iter = os.listdir(self.path_new)
        for f in list_to_iter:
            new_text = ''
            if self.use_ram:
                text_array = f.split('#')
            else:
                with open(self.path_new + f,'r', encoding='utf-8') as one_doc:
                    text_array = one_doc.read().split('#')
            current_number = 0
            for words in text_array:
                words = words.replace('\n', ' ').replace('\ufeff', '')
                if re.match('^[0-9]+$', words):
                    if words != '':
                        current_number = int(words)
                elif words == 'DELETE':
                    current_number = 0
                else:
                    new_text += words[current_number:]
                    current_number = 0
            if '**' in new_text:
                new_sents = self.create_sentence_function(new_text)
                for key in all_sents:
                    all_sents[key] += new_sents[key]
        for key in all_sents:
            print('Writing '+key+' questions, '+str(len(all_sents[key]))+' total ...')
            if '_variant' in key:
                ex_type = '_'.join(key.split('_')[:-1])
                self.write_func[ex_type](all_sents[key], key)
            else:
                self.write_func[key](all_sents[key],key)
        if not self.use_ram:
            if not self.keep_processed:
                shutil.rmtree('./processed_texts/')

        if self.maintain_log:
            self.write_log()
        if self.file_output:
            print('done, saved to' + self.output_path)
        else:
            print('done, saved in RAM as BytesIO object')

    def write_log(self):
        path_to_save = self.output_path+'/{}log.csv'.format(self.log_name)
        with open(path_to_save,'w',encoding='utf-8') as l:
            writer = csv.DictWriter(l,self.fieldnames)
            writer.writeheader()
            writer.writerows(self.log)
            print ('log saved to: ', path_to_save)

def main(path_to_data = None,exercise_types = None,output_path = None,error_types = None,mode = 'direct_input',
context = True, maintain_log = True, show_messages = False, bold = True, use_ram = False, ann = None, text =None):
    e = Exercise(path_to_realecdata = path_to_data, exercise_types = exercise_types, output_path = output_path,
     ann = ann, text = text, error_types = error_types, bold=bold, context=context,mode=mode, maintain_log=maintain_log,
     show_messages=show_messages,use_ram = use_ram)
    e.make_data_ready_4exercise()
    e.make_exercise()

def console_user_interface():
    print('Welcome to REALEC English Test Maker!')
    print('''2016-2018, Russian Error-Annotated Learners' of English Corpus research group,
HSE University,
Moscow.
''')
    path_to_data = input('Enter path to corpus data:    ')
    exercise_types = input('Enter exercise types separated by gap:    ').lower().split()
    if 'multiple_choice' in exercise_types:
        print('''
Warning! Multiple choice feature is experimental and not available for all type of erros.
To proceed, enter either 'Number','Preposotional_noun Prepositional_adjective Prepositional_adv Prepositional_verb',
'Choice_in_cond Form_in_cond Incoherent_in_cond' in the next field.
''')
    error_types = input('Enter error types separated by gap:    ').split()
    output_path = input('Enter path to output files:     ')
    context = input('Do you want to include contexts?     ').strip().lower()
    if context == 'yes':
        context = True
    else:
        context = False
    main(path_to_data, exercise_types, output_path, error_types,mode='folder',context=context,bold = True)

def test_launch():
    error_types = ['Tense_choice','Tense_form','Voice_choice','Voice_form',
                    'Infinitive_constr','Gerund_phrase','Infinitive_with_to',
                    'Infinitive_without_to_vs_participle','Verb_Inf_Gerund',
                    'Verb_part','Verb_Inf','Verb_Bare_Inf','Participial_constr',
                    'Number','Standard','Num_form','Incoherent_tenses','Incoherent_in_cond',
                    'Tautology','lex_part_choice','Prepositional_adjective','Prepositional_noun']
    
    main('./IELTS' ,['open_cloze','short_answer','word_form'], './moodle_exercises/', error_types = error_types, mode='folder')

def test_ideally_annotated():
    for ex_type in ('open_cloze', 'short_answer', 'word_form'):
        for context in (True, False):
            print(ex_type, context)
            main(path_to_data = './ideally_annotated', exercise_types = [ex_type], output_path = './ideally_annoted_output',
             error_types = [], mode='folder', context=context, maintain_log = True, show_messages = False, bold = True)

def test_with_ram():
    for ex_type in ('open_cloze', 'short_answer', 'word_form'):
        for context in (True, False):
            print(ex_type, context)
            main(path_to_data = './test_with_ram_input/AAl_12_2.ann', exercise_types = [ex_type], use_ram = True,
             output_path = './test_with_ram_output_file_input', error_types = [], mode='file', context=context,
              maintain_log = True, show_messages = True, bold = True)

def test_direct_input():
    with open (r'./2nd-year-thesis/realec_dump_31_03_2018/exam/exam2014/DZu_23_2.txt','r',encoding='utf-8') as inp:
        text = inp.read()
    with open (r'./2nd-year-thesis/realec_dump_31_03_2018/exam\exam2014\DZu_23_2.ann','r',encoding='utf-8') as inp:
        ann = inp.read()
    #for ex_type in ('open_cloze', 'short_answer', 'word_form'):
    main(ann=ann, text=text, exercise_types = ['open_cloze', 'short_answer', 'word_form'], use_ram = True,
     output_path = './test_with_direct_input_output_file_input', error_types = [], mode='direct_input', context=False,
      maintain_log = True, show_messages = True, bold = True)

def generate_exercises_from_essay(essay_name, context=False, exercise_types = ['short_answer'],file_output = True,
 write_txt = False, use_ram = True, output_file_names = None, keep_processed = False, maintain_log = False, hier_choice = False,
 make_two_variants = False, exclude_repeated = False, output_path = './test_with_two_variants'):
    helper = realec_helper.realecHelper()
    helper.download_essay(essay_name, include_json = False, save = False)
    e = Exercise(ann=helper.current_ann, text=helper.current_text,
     exercise_types = exercise_types, use_ram = use_ram,
     output_path = output_path, error_types = [], mode='direct_input', context=context,
     maintain_log = maintain_log, show_messages = False, bold = True, file_output = file_output, write_txt = write_txt, output_file_names = output_file_names,
     keep_processed = keep_processed, hier_choice = hier_choice, make_two_variants = make_two_variants, exclude_repeated = exclude_repeated)
    e.make_data_ready_4exercise()
    e.make_exercise()
    if file_output:
        return e.output_file_names
    else:
        return e.output_objects

def test_with_realec_helper():
    # essay_name = '/exam/exam2014/DZu_23_2'
    essay_name = 'http://www.realec.org/index.xhtml#/exam/exam2017/EGe_105_2'
    essay_paths = generate_exercises_from_essay(essay_name)
    print(essay_paths)

def test_with_relations():
    # essay_name = "http://realec.org/index.xhtml#/exam/exam2017/EGe_101_1"
    essay_name = "http://realec.org/index.xhtml#/exam/exam2017/EGe_105_2"
    essay_paths = generate_exercises_from_essay(essay_name, use_ram=False)
    print(essay_paths)

if __name__ == '__main__':
#    console_user_interface()
#    test_launch()
#    test_ideally_annotated()
#    test_direct_input()
    # test_with_realec_helper()
    # file_objects = generate_exercises_from_essay('/exam/exam2014/DZu_23_2', file_output = False, write_txt = False)
    # for i in file_objects:
    #     print(i, file_objects[i].getvalue())
    file_addrs = generate_exercises_from_essay('http://realec.org/index.xhtml#/exam/exam2017/EGe_105_2', file_output = True, write_txt = False, use_ram=False,
    keep_processed=True, maintain_log = True, hier_choice = True, make_two_variants = True, exclude_repeated = True, context = True)
    for i in file_addrs:
        print(i, file_addrs[i])
    # console_user_interface()