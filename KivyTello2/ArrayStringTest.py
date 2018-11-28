import os


file_name = 'text'
dirArray = []

for f in os.listdir('C:\\Users\\T\'uKeyan\\Documents\\interns2018\\KivyTello2'):
    dirArray.append(f)

y = -1
z = 0
for x in dirArray:
    y += 1
    if "text" in dirArray[y]:
        z +=1

print("The amount of files containing 'text' is: " + str(z))