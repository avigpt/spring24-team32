import pandas as pd
from sklearn.metrics import confusion_matrix, accuracy_score, precision_score, recall_score, f1_score
from automated_report import AutomatedReport
import asyncio
from report import Category
import csv

# Load data
data = pd.read_csv('data.txt')

# Separate messages and labels
messages = data['message'].tolist()
true_labels = data['label'].tolist()

async def test_function(test):
    await test.generate_report()
    if test.report_data['category'] == Category.SEXUAL_THREAT: 
        return 1
    else: 
        return 0
        
predictions = []
author = "Sample Name"
# since you can't test all 100 at one time due to gemini constraints, you can use these indexes to only look at some at a time
start = 90
end = 101
for i in range(start, end): 
    print(i)    # keep track of what the model is currently on
    test = AutomatedReport(messages[i], author)
    prediction = asyncio.run(test_function(test))
    predictions.append(prediction)
    
# note: I had code that added the predictions list to a file, but deleted it since we already have all of the predictions

# compare the incorrect predictions to the actual label and message
# with open('predictions.txt', 'r') as file:
#     line = file.readline().strip()
#     predictions = list(map(int, line.split(',')))
# 
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