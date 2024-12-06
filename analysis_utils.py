# Note: Please note that Storyboard is refereed to as Galley and Control as Original Video in the code
# Importing relevant packages
import csv
import numpy as np
from pathlib import Path
import pandas as pd
import statsmodels.formula.api as smf
from io import StringIO

def generate_answers():
    "Function to get the dataframe with GT"
    # control, video, gallery, text
    Answers = [
        ['1','2','0',None,'Left', 'No', 'Yes - unsuccessfully',None,None,],
        ['2','0','1',None,'No one','Yes - successfully', 'No',None,None,],
        ['1','0','>2',None,'1 spot and 1 ATR','No','Yes',None,None,],
        ['0','>2','2',None,'Middle','Yes','No',None,None,],
    ]

    answers = dict(
        control=dict(object0='1', object1= '2', object2= '0', event0='Left', event1='No', event2='Yes - unsuccessfully'),
        video  =dict(object0='2', object1= '0', object2= '1', event0='No one', event1='Yes - successfully', event2='No'),
        gallery=dict(object0='1', object1= '0', object2='>2', event0='1 spot and 1 ATR', event1='No',event2='Yes'),
        text   =dict(object0='0', object1='>2', object2= '2', event0='Middle', event1='Yes',event2='No'),
    )
    answers = pd.DataFrame(answers, dtype='category').unstack()
    return answers

def generate_original_df():
    "Function to get all the answers by users to one dataframe"
    # pids
    Generic = [1716183785, 1716876511, 1717120810, 1717131459, 1717397015, 1717564720, 1717728874, 1717733186, 1717736793, 1718328276, 1718332513, 1718341986, 1718582101,1718842633, 1718927553]
    Query = [1716167827, 1716858061, 1717113410, 1717386850, 1717550615, 1717553072, 1717638789, 1717649161, 1717721673, 1718065519, 1718081414, 1718337586, 1718586058, 1718848877, 1719270641]

    dir = Path('ParticipantData')
    df = {}
    csv_format = dict(
        object0='category',
        object1='category',
        object2='category',
        object_conf='int',
        event0='category',
        event1='category',
        event2='category',
        event_conf='int',
    )

    expertise_cat = pd.CategoricalDtype(["Novice", "Advanced Beginner", "Competent", "Proficient", "Expert"], ordered=True)
    familiarity_cat = pd.CategoricalDtype(["Not Familiar at all", "Somewhat familiar", "Moderately familiar", "Quite familiar", "Very familiar"], ordered=True)
    trust_cat = pd.CategoricalDtype(["Strongly distrust", "Distrust", "Neutral", "Trust ", "Strongly trust"], ordered=True)
    frequency_cat = pd.CategoricalDtype(["Never", "Rarely", "Sometimes", "Often", "Daily"], ordered=True)

    csv_format_fam = dict(
        exp_robots=expertise_cat,
        exp_envs=familiarity_cat,
        exp_subT=familiarity_cat,
        freq_robot=frequency_cat,
        freq_vid=frequency_cat,
        exp_vidsum=familiarity_cat,
        exp_intervidsum=familiarity_cat,
        freq_usemodels=frequency_cat,
        trust_models=trust_cat,
    )

    csv_format_prefer = dict(
        most_prefer='category',
        most_prefer_reason='str',
        least_prefer = 'category',
        least_prefer_reason='str',
        AI_helpful = 'category',
        AI_helpful_reason = 'str'
    )

    for generic_or_query, pids in dict(Generic=Generic, Query=Query).items():
        for pid in pids:
            row = {}
            fam = pd.read_csv(
                f'{dir/generic_or_query/str(pid)}/Familiarity Questions.csv',
                names=csv_format_fam.keys(), 
                dtype=csv_format, 
                nrows=1
            ).astype(csv_format_fam)
            row |= {'familiarity': fam}

            prefer = pd.read_csv(
                f'{dir/generic_or_query/str(pid)}/Few extra questions.csv',
                names=csv_format_prefer.keys(), 
                dtype=csv_format, 
                nrows=1
            ).astype(csv_format_prefer)
            row |= {'preference': prefer}

            for i, modality in enumerate(['Control', 'Video', 'Gallery', 'Text']):
                ## Modality file
                path = dir/generic_or_query/str(pid)/(
                    'Original Video.csv' if modality == 'Control' else
                    f'{generic_or_query} Summary {modality}.csv'
                )
                qns = pd.read_csv(path, names=csv_format.keys(), dtype=csv_format, nrows=1).astype(csv_format)  # dtype not quite working here
                time = pd.read_csv(path, names=['time'], dtype='float', skiprows=1, nrows=1)
                row |= {modality.lower(): pd.concat([qns, time], axis='columns')}

                ## Usability file
                path = path.with_stem(path.stem+' Usability')
                qns = pd.read_csv(path, header=None, nrows=1)
                row |= {modality.lower()+'_usability': qns}

            row = pd.concat(row, axis='columns')
            df |= {(pid, generic_or_query): row}

    df = pd.concat(df, axis='index', names=['pid', 'generic_or_query']).droplevel(-1)

    expert_mapping = {"Novice": 1, "Advanced Beginner": 2, "Competent": 3, "Proficient": 4, "Expert":5}
    familiarity_mapping = {"Not Familiar at all": 1, "Somewhat familiar": 2, "Moderately familiar": 3, "Quite familiar": 4, "Very familiar": 5}
    trust_mapping = {"Strongly distrust": 1, "Distrust": 2, "Neutral": 3, "Trust ": 4, "Strongly trust": 5}
    frequency_mapping = {"Never": 1, "Rarely": 2, "Sometimes": 3, "Often": 4, "Daily": 5}
    
    for c in ['exp_robots','exp_envs', 'exp_subT', 'freq_robot', 'freq_vid','exp_vidsum', 'exp_intervidsum', 'freq_usemodels', 'trust_models']:
        if c == 'exp_robots':
            df[('familiarity', c)] = df[('familiarity', c)].cat.rename_categories(expert_mapping).infer_objects(copy=False)
        elif c == 'exp_envs' or c=='exp_subT' or c=='exp_vidsum' or c == 'exp_intervidsum':
            df[('familiarity', c)] = df[('familiarity', c)].cat.rename_categories(familiarity_mapping).infer_objects(copy=False)
        elif c == 'freq_robot' or c == 'freq_vid' or c == 'freq_usemodels':
            df[('familiarity', c)] = df[('familiarity', c)].cat.rename_categories(frequency_mapping).infer_objects(copy=False)
        else:
            df[('familiarity', c)] = df[('familiarity', c)].cat.rename_categories(trust_mapping).infer_objects(copy=False)
            
    return df

def generate_ordered_df(df):
    "Function to add an order column for each task"
    orders_df = []
    for row in df.itertuples(index=True):
        pid, generic_or_query = row.Index
        path = f'ParticipantData/{generic_or_query}/{pid}/answers.csv'
        with open(path) as file:
            header: list = next(csv.reader(file))
        patterns = dict(
            control="Original Video:",
            text   =f"{generic_or_query} Summary Text:",
            gallery=f"{generic_or_query} Summary Gallery:",
            video  =f"{generic_or_query} Summary Video:",
        )
        orders = dict(zip(
            patterns.keys(),
            np.argsort([
                next(i for i, title in enumerate(header) if pattern in title)
                for pattern in patterns.values()
            ]),
        ))
        for modality, order in orders.items():
            orders_df.append(dict(pid=pid, generic_or_query=generic_or_query, modality=modality, order=order))
    orders_df = pd.DataFrame(orders_df).set_index(['pid','generic_or_query','modality']).unstack('modality').reorder_levels([1,0], 'columns')

    df_w_order = pd.concat([df, orders_df], axis='columns')
    df_w_order.reindex(df_w_order.columns, axis='columns')
    return df_w_order

def define_df_comparison(answers, df_w_order, scoreCal=True):
    """
    This function compares the correct answer to those provided and returns 1 if correct, 0 for every other answer
    scoreCal: 
        If you are calculating the accuracy keep this True. 
        If False, it will output 1 if the participant has provided 'Not sure' as the answer and 0 for every other answer. 
    """
    df_qns, answers = df_w_order.align(answers, axis='columns', join='right')
    if scoreCal:
        return df_qns == answers
    else:
        return df_qns == 'Not sure'

def generate_df_queries():
    "This function will return a dataframe with all the queries each user made"
    Generic = [1716183785, 1716876511, 1717120810, 1717131459, 1717397015, 1717564720, 1717728874, 1717733186, 1717736793, 1718328276, 1718332513, 1718341986, 1718582101,1718842633, 1718927553]
    Query = [1716167827, 1716858061, 1717113410, 1717386850, 1717550615, 1717553072, 1717638789, 1717649161, 1717721673, 1718065519, 1718081414, 1718337586, 1718586058, 1718848877, 1719270641]
    df = {}
    for _, pids in dict(Generic=Generic, Query=Query).items():
        for pid in pids:
            a = {}
            for modality in ['Gallery', 'Video', 'Text']:
                try:
                    with open(f'ParticipantData/Query/{pid}/Query Summary {modality}_queries.txt', "r") as file:
                        all_lines = file.readlines()
                        lines = len(all_lines)
                        query = " ".join(all_lines)
                        # print(pid, modality, lines)
                        a |= {('queries', f'{modality.lower()}'): query}
                        a |= {('queries', f'{modality.lower()}_len'): lines}
                except:
                        a |= {('queries', f'{modality.lower()}'): None}
                        a |= {('queries', f'{modality.lower()}_len'): 0}
            df |= {pid: a}
    df = pd.DataFrame.from_dict(df).transpose()
    return df

def generate_df_w_qtype(df_in):
    "This function returns the input dataframe with additional columns about question type"
    df_in.columns.set_names(['modality','qname'], inplace=True)
    df_long = df_in.stack(['modality','qname'], future_stack=True)
    df_long.name = "correct"
    df_long = df_long.reset_index()
    df_long["object_or_event"] = df_long.qname.str[:-1]
    df_long["qid"] = df_long.modality + "_" + df_long.qname
    return df_long

def generate_df_for_analysis(df_compare, df_order):
    "Preparing the dataframe fit for analysis. Define the columns types etc."
    df = generate_df_w_qtype(df_compare)
    df = df.join(df_order, on=['pid','generic_or_query','modality'])
    df['correct'] = df['correct'].astype('int')
    
    conditions = [
        (df['generic_or_query'] == 'Generic') & (df['modality'] == 'control'),
        (df['generic_or_query'] == 'Query') & (df['modality'] == 'control'),
        (df['generic_or_query'] == 'Generic') & (df['modality'] == 'text'),
        (df['generic_or_query'] == 'Query') & (df['modality'] == 'text'),
        (df['generic_or_query'] == 'Generic') & (df['modality'] == 'gallery'),
        (df['generic_or_query'] == 'Query') & (df['modality'] == 'gallery'),
        (df['generic_or_query'] == 'Generic') & (df['modality'] == 'video'),
        (df['generic_or_query'] == 'Query') & (df['modality'] == 'video')
    ]

    values = ['No_Summary', 'No_Summary', 'G', 'Q', 'G', 'Q', 'G', 'Q']
    df['summary'] = np.select(conditions, values, default=None)
    df['cross'] = np.select(conditions, ['C', 'C', 'GT', 'QT', 'GS', 'QS', 'GV', 'QV'], default=None)
    
    df['pid'] = df['pid'].astype('category')
    df['qid'] = df['qid'].astype('category')

    df['summary'] =  pd.Categorical(df['summary'], categories=['No_Summary','G','Q'], ordered=False)
    df['cross'] =  pd.Categorical(df['cross'], categories=['C','GT','QT','GS', 'QS', 'GV', 'QV'], ordered=False)

    df['object_or_event'] = pd.Categorical(df['object_or_event'], categories=['object', 'event'], ordered=False)

    df['order'] = pd.Categorical(df['order'], ordered=True, categories=[0, 1, 2, 3])
    df['correct'] = df['correct'].astype('int')
    df['modality'] =  pd.Categorical(df['modality'], categories=['control','video', 'text','gallery'], ordered=False)

    return df

def get_query_generation_time():
    "Return a dataframe with query processing adjusted times"
    Generic = [1716183785, 1716876511, 1717120810, 1717131459, 1717397015, 1717564720, 1717728874, 1717733186, 1717736793, 1718328276, 1718332513, 1718341986, 1718582101,1718842633, 1718927553]
    Query = [1716167827, 1716858061, 1717113410, 1717386850, 1717550615, 1717553072, 1717638789, 1717649161, 1717721673, 1718065519, 1718081414, 1718337586, 1718586058, 1718848877, 1719270641]
    
    df = {}
    for _, pids in dict(Generic=Generic, Query=Query).items():
        for pid in pids:
            a = {}
            for modality in ['Gallery', 'Video', 'Text']:
                try:
                    with open(f'ParticipantData/Query/{pid}/Query Summary {modality}_timetaken.txt', "r") as file:
                        all_lines = file.readlines()
                        lines = len(all_lines)
                        duration = np.array([float(line.split("=")[1].strip()) for line in all_lines]).sum()
                        a |= {('queries', f'{modality.lower()}_gentime'): duration}
                        a |= {('queries', f'{modality.lower()}_len'): lines}
                except:
                        a |= {('queries', f'{modality.lower()}_gentime'): None}
                        a |= {('queries', f'{modality.lower()}_len'): 0}
            df |= {pid: a}
    df = pd.DataFrame.from_dict(df).transpose()

    df.columns = df.columns.set_names('useless', level=0)
    df = df.stack('useless', future_stack=True)
    df = df.reset_index()
    df.rename(columns={'level_0': 'pid'}, inplace=True)
    df.dropna(inplace=True)
    
    df_new = None
    for i in ['gallery', 'video', 'text']:
        df_tmp = df[['pid', f'{i}_gentime']].copy()
        df_tmp['query_gentime'] = df_tmp.pop(f'{i}_gentime').astype('float')
        df_tmp['modality'] = f'{i}'

        if df_new is None:
            df_new = df_tmp
        else:
            df_new = pd.concat([df_new, df_tmp])
    return df_new

def generate_df_from_string_table(text, generic_or_query):
    "Generates a dataframe from a string"
    model_table = StringIO(text)
    df = pd.read_table(model_table, index_col=0, header=[0,1], dtype=str, na_values=["?"])
    df.index.name = "pid"
    df.columns.names = ["modality", "qname"]
    df = df.stack(["modality", "qname"], future_stack=True)
    df.name = "model_answer"
    df = df.to_frame()
    df["generic_or_query"] = f"{generic_or_query}"
    df = df.set_index("generic_or_query", append=True)
    return df

### The following strings are added after manually labelling the model produced G and Q summaries.
# * Under Q: ? = Question where the users did not query
# * Under G: For any user, per question it is the same answer, since there is one G summary for each modality

text_Q = """\
	video	video	video	video	video	video	gallery	gallery	gallery	gallery	gallery	gallery	text	text	text	text	text	text
	object0	object1	object2	event0	event1	event2	object0	object1	object2	event0	event1	event2	object0	object1	object2	event0	event1	event2
1716167827	0	0	0	No one	Yes - successfully	No	1	0	1	1 spot and 1 ATR	No	No	>2	>2	>2	Left	Yes	No
1716858061	0	0	0	No one	Yes - successfully	?	1	0	1	No one	No	No	>2	>2	>2	Left	Yes	Yes
1717113410	0	0	0	No one	Yes - successfully	No	1	0	>2	1 spot	No	No	>2	>2	2	Right	No	Yes
1717386850	2	0	0	?	Yes - successfully	No	1	0	1	1 spot	?	?	1	>2	>2	Left	Yes	Yes
1717550615	0	0	?	?	Yes - successfully	No	1	?	?	?	No	?	0	1	1	?	?	?
1717553072	2	0	1	?	Yes - successfully	No	1	0	>2	1 spot and 1 ATR	No	Yes	>2	>2	>2	?	Yes	Yes
1717638789	2	0	1	?	Yes - successfully	No	1	0	>2	No one	No	Yes	>2	2	2	Left	Yes	No
1717649161	0	0	0	?	Yes - successfully	?	1	0	1	1 spot	No	Yes	>2	>2	1	Not sure	?	No
1717721673	?	0	1	No one	Yes - successfully	No	1	0	1	1 spot	No	Yes	>2	2	1	Left	Yes	No
1718065519	2	0	1	No one	Yes - successfully	No	1	0	>2	1 spot and 1 ATR	No	Yes	>2	>2	1	Left	Yes	No
1718081414	0	0	0	No one	?	?	1	0	>2	1 spot and 1 ATR	No	Yes	>2	>2	>2	Left	Yes	?
1718337586	2	0	0	?	Yes - successfully	No	1	0	1	1 spot and 1 ATR	No	?	>2	>2	>2	Left	Yes	No
1718586058	2	0	1	No one	Yes - successfully	No	1	0	>2	1 spot	No	Yes	1	1	1	Left	Yes	No
1718848877	2	0	1	No one	Yes - successfully	No	1	0	>2	?	No	No	>2	>2	>2	Left	?	No
1719270641	0	0	0	No one	Yes - successfully	No	1	0	1	1 spot	No	No	2	2	2	Left	Yes	No
"""

text_G = """\
	video	video	video	video	video	video	gallery	gallery	gallery	gallery	gallery	gallery	text	text	text	text	text	text
	object0	object1	object2	event0	event1	event2	object0	object1	object2	event0	event1	event2	object0	object1	object2	event0	event1	event2
pid																		
1716183785	2	0	1	No one	Yes - successfully	No	0	0	0	No one	No	Yes	0	0	0	Left	No	No
1716876511	2	0	1	No one	Yes - successfully	No	0	0	0	No one	No	Yes	0	0	0	Left	No	No
1717120810	2	0	1	No one	Yes - successfully	No	0	0	0	No one	No	Yes	0	0	0	Left	No	No
1717131459	2	0	1	No one	Yes - successfully	No	0	0	0	No one	No	Yes	0	0	0	Left	No	No
1717397015	2	0	1	No one	Yes - successfully	No	0	0	0	No one	No	Yes	0	0	0	Left	No	No
1717564720	2	0	1	No one	Yes - successfully	No	0	0	0	No one	No	Yes	0	0	0	Left	No	No
1717728874	2	0	1	No one	Yes - successfully	No	0	0	0	No one	No	Yes	0	0	0	Left	No	No
1717733186	2	0	1	No one	Yes - successfully	No	0	0	0	No one	No	Yes	0	0	0	Left	No	No
1717736793	2	0	1	No one	Yes - successfully	No	0	0	0	No one	No	Yes	0	0	0	Left	No	No
1718328276	2	0	1	No one	Yes - successfully	No	0	0	0	No one	No	Yes	0	0	0	Left	No	No
1718332513	2	0	1	No one	Yes - successfully	No	0	0	0	No one	No	Yes	0	0	0	Left	No	No
1718341986	2	0	1	No one	Yes - successfully	No	0	0	0	No one	No	Yes	0	0	0	Left	No	No
1718582101	2	0	1	No one	Yes - successfully	No	0	0	0	No one	No	Yes	0	0	0	Left	No	No
1718842633	2	0	1	No one	Yes - successfully	No	0	0	0	No one	No	Yes	0	0	0	Left	No	No
1718927553	2	0	1	No one	Yes - successfully	No	0	0	0	No one	No	Yes	0	0	0	Left	No	No
"""

def generate_model_answers_df():
    "Thi function returns the model answers"
    df_model_answer_Q = generate_df_from_string_table(text_Q, "Query")

    df_model_answer_G = generate_df_from_string_table(text_G, "Generic")

    df_model_answers = pd.concat((df_model_answer_G, df_model_answer_Q), axis=0)
    return df_model_answers


# Noise reduction
import contextlib
import sys

class DummyFile(object):
    def write(self, x): pass

@contextlib.contextmanager
def nostdout():
    save_stdout = sys.stdout
    sys.stdout = DummyFile()
    yield
    sys.stdout = save_stdout

@contextlib.contextmanager
def nostderr():
    save_stderr = sys.stderr
    sys.stderr = DummyFile()
    yield
    sys.stderr = save_stderr
