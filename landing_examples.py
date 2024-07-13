from transformers import pipeline
#

def get_sentiment():
    sentiment_pipeline = pipeline("sentiment-analysis")
    data = ["I love you", "I hate you"]
    
    return sentiment_pipeline(data)