import pandas as pd
from sklearn.metrics import confusion_matrix, accuracy_score, precision_score, recall_score, f1_score
from detection import detect_sextortion
import json
import asyncio

# Load data
data = pd.read_csv('data.txt')

# Separate messages and labels
messages = data['message'].tolist()
true_labels = data['label'].tolist()

# get openai key
with open('tokens.json') as f:
    # If you get an error here, it means your token is formatted incorrectly. Did you put it in quotes?
    tokens = json.load(f)
    openai_token = tokens['openai']

async def predict():
    predictions = []
    for i in range(len(messages)): 
        print(i)    # keep track of what the model is currently on
        has_content = await detect_sextortion(messages[i], 'gpt', openai_token)
        if has_content: 
            predictions.append(1)
        else: 
            predictions.append(0)
    return predictions
            
predictions = asyncio.run(predict())
print(predictions)

# If you want, compare the incorrect predictions to the actual label and message
# with open('predictions_openai.txt', 'r') as file:
#     line = file.readline().strip()
#     predictions = list(map(int, line.split(',')))

# for i in range(len(predictions)): 
#     if predictions[i] != true_labels[i]: 
#         print(i + 2, ":", messages[i], "|", "true label:", true_labels[i], "prediction:", predictions[i])

# Calculate confusion matrix and metrics
cm = confusion_matrix(true_labels, predictions)
accuracy = accuracy_score(true_labels, predictions)
precision = precision_score(true_labels, predictions)

# Output results
print("Confusion Matrix:")
print(cm)
print(f"Accuracy: {accuracy}")
print(f"Precision: {precision}")
