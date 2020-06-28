import shelve

user = 'tmp_files/@mzafarm'

user = shelve.open(user)
user['name'] = '@mzafarm'
user['polls'] = [
    {
        'question': 'What is that?'
    }
]

print(user['polls'][0]['question'])
