

currentSurvey = {
    'name': str,
    'allPolls': [
    ]
}

re = currentSurvey.setdefault('name', None)
print(re)

