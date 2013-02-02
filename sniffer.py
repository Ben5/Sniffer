import pprint
import glob
import sys

def main(argv):

    globalClassDictionary = {}

    # open the file and read the contents
    inputDirOrFile = argv[1]
    if inputDirOrFile.find('.php') >= 0:
        files = [inputDirOrFile]
    else:
        files = glob.glob(inputDirOrFile + '/*.php')

    for file in files:
        f = open(file, 'r')
        lines = f.readlines()

        # now tidy up the contents into a list of useful lines
        filteredLines = []

        for line in lines:
            #strip new-line characters
            newline = line.replace('\n','').strip(' ')
            # strip empty and wholly-commented lines
            if newline != "" and newline.find('//') != 0:
                filteredLines.append(newline)

        # now do the parsing and evaluating!
        globalClassDictionary[file] = ParseCode(filteredLines)

    # squirt out some output
    #print 'everything:'
    #pprint.pprint(classDictionary)

    output = ConstructOutput(inputDirOrFile, globalClassDictionary)

    # write the output to a file in httpdocs so we can access it from a browser
    outputFile = open('/opt/git/Sniffer/output/sniffer.html', 'w')
    outputFile.write(output)
    outputFile.close()

def ConstructOutput(inputDirOrFile, globalClassDictionary):
    output = '<html>'
    output += '<body>'
    output += 'checking code in: ' + inputDirOrFile

    for fileName in globalClassDictionary.keys():
        output += '<div style="border-style:solid; border-color:blue; margin:5px; padding:5px">'
        output += fileName

        classDictionary = globalClassDictionary[fileName]
        for classInstance in classDictionary:
            output += '<div style="border-style:solid; border-color:yellow; margin:5px; padding:5px">'
            output += 'class ' + classInstance

            for function in classDictionary[classInstance]['classfunctions']:
                output += '<div style="border-style:solid; border-color:red; margin:5px; padding:5px">'

                varCrazy = function['variables']['crazy']
                loopCrazy = function['loops']['crazy']
                functionsCrazy = function['functioncalls']['functions'] #['crazy']

                # find out if we have crazy in function calls:
                functionsCrazyCount = 0
                for crazy in functionsCrazy:
                    times = functionsCrazy[crazy]
                    if times > 1:
                        functionsCrazyCount += 1

                titleColour='green'
                if len(varCrazy) + len(loopCrazy) + functionsCrazyCount > 0:
                    titleColour = 'red'

                output += '<span style="background-color:'+titleColour+'">' + function['header'] + '</span><br/>'
                #print 'variables in this function:'
                #pprint.pprint( function['variables']['vars'])

                if len(varCrazy) > 0:
                    output += 'Craziness in Variables:'
                    output += '<ul>'
                    for crazy in varCrazy:
                        output += '<li>' + crazy + '</li>'
                    output += '</ul>'

                if len(loopCrazy) > 0:
                    output += 'Craziness in For Loops:'
                    output += '<ul>'
                    for crazy in loopCrazy:
                        output += '<li>' + crazy + '</li>'
                    output += '</ul>'

                if functionsCrazyCount > 0:
                    output += 'Multiple Function Calls:'
                    output += '<ul>'
                    for crazy in functionsCrazy:
                        times = functionsCrazy[crazy]
                        if times > 1:
                            output += '<li>' + crazy + '() called ' + str(times) + ' times</li>'
                    output += '</ul>'

                output += '</div>'

            output += '</div>'

        output += '</div>'

    output += '</body>'
    output += '</html>'

    return output

def GetVariables(functionLines, functionHeader):
    variables = {'vars':{}, 'assignments':{}, 'crazy':[]}

    for word in functionHeader.split():
        punctuation = ['(',')','"', ',']
        for k in punctuation:
            word = str(word).replace(k, ' ')
        if word.find('$') == 0:
            if word in variables['vars']:
                variables['vars'][word] += 1
            else:
                variables['vars'][word] = 1

    for i in range(0, len(functionLines)):
        trimmedLine = functionLines[i]
        replacements = [(';',''), (',',' '), ('.',' '), ('++',' '), ('--',' '), ('->',' '),
                       ('+',' + '), ('-',' - '),  ('[',' [ '), (']',' ] '),
                       ('(',' ( '), (')',' ) ')]
        for j,k in replacements:
            trimmedLine = trimmedLine.replace(j, k)

        wordsInLine = trimmedLine.split()
        # Get all the variables that are assigned to
        for i in range(0, len(wordsInLine)-2):
            word = wordsInLine[i]
            nextWord = wordsInLine[i+1]

            # trim all punctuation from word
            punctuation = ['(',')','"']
            for k in punctuation:
                word = str(word).replace(k, '')
            if word.find('$') == 0 and nextWord == '=':
                if word in variables['assignments']:
                    variables['assignments'][word] += 1
                else:
                    variables['assignments'][word] = 1


        # Get all the variables that exist
        for word in wordsInLine:
            # trim all punctuation from word
            punctuation = ['(',')','"']
            for k in punctuation:
                word = str(word).replace(k, '')
            if word.find('$') == 0:
                if word in variables['vars']:
                    variables['vars'][word] += 1
                else:
                    variables['vars'][word] = 1

    variables['crazy'] = CheckForCrazyInVariables(variables)

    return variables

def GetFunctionCalls(functionLines):
    functions = {'functions':{}, 'crazy':[] }

    # functions we aren't interested in:
    ignoreFunctions = ['if', 'for', 'foreach', 'array', 'trigger_error', 'trigger_warning']

    for line in functionLines:
        for chunk in line.split('(')[:-1]:
            if len(chunk.split()) > 0:
                word = chunk.split()[-1]
                if word not in ignoreFunctions:
                    if word not in functions['functions']:
                        functions['functions'][word] = 0
                    functions['functions'][word] += 1

    # todo: write CheckForCrazyInFunctionCalls!
    # functions['crazy'] = CheckForCrazyInFunctionCalls(functions['functions'])

    return functions

def GetForLoops(codeLines):
    forLoops = {'for':[], 'foreach':[], 'crazy':[]}

    for i in range(0, len(codeLines)):
        line = codeLines[i]
        # find all the for loops
        if line.find('for(') >= 0:
            loopDict = {'header':'', 'lines':[]}
            loopHeaderString = ''

            # loop over lines until you find a '{' - building up function header
            openingBraceLine = 0
            for j in range(i, len(codeLines)):
                if(codeLines[j].find('{') >= 0):
                    openingBraceLine = j
                    loopDict['header'] = loopHeaderString
                    break
                loopHeaderString += codeLines[j] + ' '

            # now loop over all the lines below the funtion header, until we get to the closing '}'
            braceDepth = 0
            for j in range(openingBraceLine, len(codeLines)):
                line = codeLines[j]
                if line.find('{') >=0:
                    braceDepth += 1
                if line.find('}') >=0:
                    braceDepth -= 1

                loopDict['lines'].append(line)

                if braceDepth == 0:
                    # we now have all the lines of code for this loop
                    forLoops['for'].append(loopDict)

                    # check for crazy!
                    crazy = CheckForCrazyInFor(loopDict['header'], loopDict['lines'])

                    if len(crazy) > 0:
                        for crazyThing in crazy:
                            forLoops['crazy'].append(crazyThing)
                    break;

            continue

        # find all the foreach loops
        if line.find('foreach(') >= 0:

            loopDict = {'header':'', 'lines':[]}
            loopHeaderString = ''

            # loop over lines until you find a '{' - building up function header
            openingBraceLine = 0
            for j in range(i, len(codeLines)):
                if(codeLines[j].find('{') >= 0):
                    openingBraceLine = j
                    loopDict['header'] = loopHeaderString
                    break
                loopHeaderString += codeLines[j] + ' '

            # now loop over all the lines below the funtion header, until we get to the closing '}'
            braceDepth = 0
            for j in range(openingBraceLine, len(codeLines)):
                line = codeLines[j]
                if line.find('{') >=0:
                    braceDepth += 1
                if line.find('}') >=0:
                    braceDepth -= 1

                loopDict['lines'].append(line)

                if braceDepth == 0:
                    # we now have all the lines of code for this loop
                    forLoops['foreach'].append(loopDict)

                    # check for crazy!
                    crazy = CheckForCrazyInForEach(loopDict['lines'])

                    if len(crazy) > 0:
                        for crazyThing in crazy:
                            forLoops['crazy'].append(crazyThing)
                    break;

            continue

        # any other types of loops...

    return forLoops

def CheckForCrazyInVariables(varDict):
    crazy = []
    allVariables = varDict['vars']
    variablesAssignedTo = varDict['assignments']

    # check for variables only being used once
    for key in allVariables.keys():
        if allVariables[key] == 1:
            #crazy.append('variable ' + key + ' is only used once, what\'s the point?')
            if key in variablesAssignedTo and variablesAssignedTo[key] == 1:
                crazy.append('variable ' + key + ' is assigned a value it never uses!')

    return crazy

def CheckForCrazyInFor(header, codeLines):
    crazy = []

    # are we calling a function in the header?
    trimmedHeader = header.replace('for(','')
    trimmedHeader = trimmedHeader.rstrip().rstrip(')')
    headerParts = trimmedHeader.split(';')
    comparison = headerParts[1]
    operator = ''
    if comparison.find('>') >= 0:
        operator = '>'
    elif comparison.find('<') >= 0:
        operator = '<'
    else:
        crazy.append('found a comparison operator that wasnt < or >')

    if operator != '':
        comparisonParts = comparison.split(operator)
         # todo - strip parts[1] of whitespace
        comparisonValue = comparisonParts[1].strip()
        if not comparisonValue.isdigit():
            if comparisonValue.find('(') != -1:
                crazy.append('you seem to be calling a function in the declaration of a for loop: ' + comparisonValue)

    # do we have another for/foreach nested in this one?
    for line in codeLines:
        if line.find('for(') >= 0 or line.find('foreach(') >= 0:
            crazy.append('you have a nested for or foreach - is this necessary?')


    # other types of crazy...

    return crazy

def CheckForCrazyInForEach(codeLines):
    crazy = []

    # do we have another for/foreach nested in this one?
    for line in codeLines:
        if line.find('for(') >= 0 or line.find('foreach(') >= 0:
            crazy.append('you have a nested for or foreach - is this necessary?')

    # other types of crazy...

    return crazy

def ParseCode(codeLines):
    classNames = []
    classDictionary = {}

    for i in range(len(codeLines)):
        if codeLines[i].find('class') == 0:
            if codeLines[i+1] == '{':
                classNames.append( (codeLines[i].replace('class ', ''), i) )

    for className,lineNo in classNames:
        classDict = {'codelines':[], 'classfunctions':[]}

        braceDepth = 0

        for i in range(lineNo+1,len(codeLines)):
            if codeLines[i].find('{') >=0:
                braceDepth += 1
            if codeLines[i].find('}') >=0:
                braceDepth -= 1

            classDict['codelines'].append(codeLines[i])
            if braceDepth == 0:
                break;


        # find all the functions in each class
        classCodeLines = classDict['codelines']
        for i in range(0, len(classCodeLines)):
            functionHeaderString = ''

            if classCodeLines[i].find(' function') >= 0:
                functionDict = {'header':'', 'lines':[], 'variables':{}, 'loops':{}, 'functioncalls':{}}

                # loop over lines until you find a '{' - building up function header
                openingBraceLine = 0
                for j in range(i, len(classCodeLines)):
                    if(classCodeLines[j].find('{') >= 0):
                        openingBraceLine = j
                        functionDict['header'] = functionHeaderString
                        break
                    functionHeaderString += classCodeLines[j] + ' '

                # now loop over all the lines below the funtion header, until we get to the closing '}'
                braceDepth = 0
                for j in range(openingBraceLine, len(classCodeLines)):
                    line = classCodeLines[j]
                    if line.find('{') >=0:
                        braceDepth += 1
                    if line.find('}') >=0:
                        braceDepth -= 1

                    functionDict['lines'].append(line)

                    if braceDepth == 0:
                        # we now have all the lines of code for this function
                        # let's do something with them!
                        # start off by getting all the variable info from them
                        functionLines = functionDict['lines']
                        functionHeader = functionDict['header']
                        functionDict['variables'] = GetVariables(functionLines, functionHeader)

                        # now look for crazy in the for loops
                        functionDict['loops'] = GetForLoops(functionLines)

                        # now look for all the function calls in this function
                        functionDict['functioncalls'] = GetFunctionCalls(functionLines);

                        classDict['classfunctions'].append(functionDict)
                        break;

        classDictionary[className] = classDict
    return classDictionary


if __name__ == '__main__':
    main(sys.argv)

