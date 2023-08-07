from django.shortcuts import render
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django import forms
from django.http import HttpResponseRedirect, HttpResponse
from django.urls import reverse
import requests, os, openai
import json
from django import forms
from pyfiglet import Figlet
from .helpers import *
from dotenv import load_dotenv
from .models import Memory, Biographyitem, Chat, Domain




class NewLoginForm(forms.Form):
    username = forms.CharField(widget=forms.Textarea(attrs={'rows': 1, 'cols': 10, 'class': 'textarea'}),label="username")
    password = forms.CharField(widget=forms.Textarea(attrs={'rows': 1, 'cols': 10, 'class': 'textarea'}),label="Password")

class NewChatForm(forms.Form):
  
    usercontent = forms.CharField(widget=forms.Textarea(attrs={'rows': 4, 'cols': 58, 'class': 'textarea', 'placeholder':'Say something...'}), max_length=500, label="")
    startnewchat = forms.BooleanField(widget=forms.CheckboxInput(attrs={ 'class': 'topicboo'}),label="Start new chat?", required=False)

class NewMemoryForm(forms.Form):
    date = forms.DateField(widget=forms.DateInput(attrs={'rows': 1, 'cols': 10, 'class': 'textarea'}),label="date (YYYY-MM-DD)")
    emotion = forms.CharField(widget=forms.Textarea(attrs={'rows': 1, 'cols': 10, 'class': 'textarea'}),label="emotion")
    description = forms.CharField(widget=forms.Textarea(attrs={'rows': 1, 'cols': 10, 'class': 'textarea'}),label="description")
    content = forms.CharField(widget=forms.Textarea(attrs={'rows': 4, 'cols': 50, 'class': 'textarea memorycontent'}),label="content")

class DeleteMemoryForm(forms.Form):
    deletememoryboo = forms.BooleanField(label="Forget?" )

class NewBioForm(forms.Form):
    item = forms.CharField(widget=forms.Textarea(attrs={'rows': 1, 'cols': 10, 'class': 'textarea'}),label="item")
    description = forms.CharField(widget=forms.Textarea(attrs={'rows': 1, 'cols': 10, 'class': 'textarea'}),label="description")

class DeleteBioForm(forms.Form):
    deletebioboo = forms.BooleanField(label="delete this fact?" )

class DomainsListForm(forms.ModelForm):
    domain = forms.CharField(widget=forms.Textarea(attrs={'style': 'width:300px', 'rows':2, 'mincols':30, 'class': 'textarea'}), label="",)
    class Meta:
        model = Domain
        fields = ['domain'] 
        labels = {
            "domain": "",
        }      

class SelectAgentForm(forms.Form):
    def __init__(self, *args, agentslist=[], **kwargs):
        super(SelectAgentForm, self).__init__(*args, **kwargs)
        self.fields['agent'] = forms.ChoiceField(
            choices=[(agentname, agentname) for i, agentname in enumerate(agentslist)],
            widget=forms.RadioSelect,
            required=False, label='',
        )



load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

def login_view(request):
    if request.method == "POST":
        print(">>> loginview POST")
        form = NewLoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data["username"]
            password = form.cleaned_data["password"]
            print(">>> username ", username)
            user = authenticate(request, username=username, password=password)
            if user:
                login(request, user)
                # domainslist
                if not Domain.objects.filter(user=request.user).exists():
                    defaultdomain = Domain(domain='general',user=request.user)
                    defaultdomain.save()
                return HttpResponseRedirect(reverse("ayou:chat"))
            # else:
            #     return render(
            #         request,
            #         "ayou/index.html",
            #         {"form": NewLoginForm()},
            #     )
        else:
            return render(
                request,
                "ayou/index.html",
                {"form": NewLoginForm(), 'pagebodyclass':'indexbodyclass', 'pagemenuwideclass':'indexmenuwideclass','pagelineheightclass':'indexlineheightclass' },
            )

    form = NewLoginForm()
    if not request.user.is_authenticated:
        print(">>> loginview get request : not loged in")
        messages.add_message(request, messages.INFO, "Please log in.")
        return render(request, "ayou/index.html", {"form": NewLoginForm(),'pagebodyclass':'indexbodyclass', 'pagemenuwideclass':'indexmenuwideclass','pagelineheightclass':'indexlineheightclass', 'pageborderlneclass':'indexborderlineclass'})
    else:
        messages.add_message(request, messages.INFO, "logged in")
        return HttpResponseRedirect(reverse("ayou:chat"))

def register_view(request):
    
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data["username"]
            messages.success(request, f'New account created. Now you can log-in as {username}')
            print(f'>>> in registerview : account created for {username}')
            return HttpResponseRedirect(reverse( 'ayou:login'))
        else:
            messages.add_message(request, messages.INFO, "Fill in the form correctly")
            return render(request, 'ayou/register.html', {'form': form})
        
    heading = figlettext('Sign up and start building your clone', 'small')    
    form = UserCreationForm()
    messages.add_message(request, messages.INFO, "Register")
    return render(request, 'ayou/register.html', {'form': form, 'heading': heading,'pagebodyclass':'registerbodyclass', 'pagemenuwideclass':'registermenuwideclass','pagelineheightclass':'registerlineheightclass'})

@login_required
def logout_view(request):
    logout(request)
    message = "Logged out"
    return HttpResponseRedirect(reverse("ayou:login"))

@login_required
def chat(request):

    def systemmessage(name, sentences=5):
        print('++++ systemmessage() called')
        systemmessage = {"role": "system", "content": f"You are a character called {name} and here are some details about you  {biographyitems}. Of course you have memories and  feelings. If the user asks you about a memory, you can look at your 'getmemorycontent' function. You  can also consult other agents for more information using the 'askotheragent' function.  Keep your answers to about {sentences} sentences.  Please always reply in character, and never say you are an A.I.!]"}
        return systemmessage
    
    def exampleassistantmessage(name):
        print('+++++ exampleassistantmessage() called')
        result ={"role": "assistant", "content": f"Hello! My names {name}.  I remember quite a bit about my past. Not all my memories are happy, but I'm willing to share them with you. I'm also happy to answer any questions you have about what I'm doing now, or about my past.I can also ask other clones for information about their memories."}
        return result
    
    def dealwithfunctionrequest():
        print('+++ dealwithfunctionrequest() called')
        possfunctions = {"getmemorycontent": getmemorycontent, "askotheragent": askotheragent}
        functionname = completionmessage["function_call"]["name"]
        functiontocall = possfunctions[functionname]
        print('... functiontocall ', functiontocall)
        functionargs = json.loads(completionmessage["function_call"]["arguments"])
        print('... functionargs ', functionargs)
                    ##### completion call here!
        functionresponse = functiontocall(**functionargs)
        # print('... functionresponse= ', functionresponse, type(functionresponse))
        messagechain.append(
            {
                "role": "function",
                "name": functionname,
                "content": functionresponse,
            }
        )
        return messagechain
    
    def askotheragent(agentname, question):
  
        def askotheragentcompletion(callfunction='auto'):
            print('+++ askotheragentcompletion() called')
            completion = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=messagechain,
                max_tokens=1000,
                temperature=1,
                functions=otheragentsfunctions,
                function_call="auto",
            )
            # print(f'/// askotheragentcompletion(): completion = {completion}')
            return completion
        """
        redefine variables and chat, with local scope, to the other agent
        """        
        attempts = 0
        print(f'+++ askotheragent() called= {agentname}')
        print(f'+++ with this question= {question}')
        otheragentid= User.objects.get(username=agentname).id
        print(f'/// otheragentid ={otheragentid}')
        memorieslist = getmemorieslist(otheragentid)
        otheragentsdomainslist = otheragentdomainsfunction(otheragentid)
        otheragentsfunctions = scopedfunctions(memorieslist, otheragentsdomainslist)
        print(f'/// {agentname}"s functions ={otheragentsfunctions}')
        print(f'/// {agentname}s memorieslist ={memorieslist}')
        messagechain = []
        messagechain.append(systemmessage(agentname))
        messagechain.append({"role": "system", "content": "IMPORTANT! Make sure you have the correct id for the memory you want to retrieve"})
        messagechain.append(exampleassistantmessage(agentname))
      
        print(f'/// {agentname}s messagechain {messagechain}')
        print('///////  about to make the first completion to otheragent')
                    

                    ###### if no request for a memory+id, loop until you get one

        for i in range(5):
            askotheragentresponse  = (askotheragentcompletion())
            print(f'/// askotheragentresponse = {askotheragentresponse}')
            print(f'/// askotheragentresponse type = {type(askotheragentresponse)}')
            functioncall =  askotheragentresponse['choices'][0]['message'].get('function_call')
            print(f'/// functioncall = {functioncall}')
            arguments = askotheragentresponse['choices'][0]['message']['function_call']['arguments']
            print(f'/// arguments = {arguments}')
            # is a string
            print(f'/// arguments type = {type(arguments)}')
            argumentsdict= json.loads(arguments)
            print(f'/// argumentsdict = {argumentsdict}')
            memoryid=argumentsdict['memory_id']
            print(f'/// memoryid = {memoryid}')
                    ##### check if there is both memory and id
            if (functioncall is not None) and (memoryid is not None):
                print('/// response has function call and id')
                        ##### check id matches a memory 
                            ##### destringify the args    
                argsstring = askotheragentresponse['choices'][0]['message']['function_call']['arguments']
                argsdict = json.loads(argsstring)
                print(f'/// argsdict = {argsdict}')
                memoryid = argsdict.get('memory_id')
                if  Memory.objects.filter(id=memoryid):
                        #### you have an id and a matching memory so get the memory
                    newmessage = f"Here is some information from someone you know. Do not say it is your memory!  {getmemorycontent(memoryid)}  Use it to answer the original users question."
                    print(f'>>> askotheragent() retrieved memory= {newmessage}')
                    #### we got the memory, now we need to send it back to the original agent
                    return newmessage

                else:
                    print('... in loop-memory id not valid')
                    print(f'/// invalid memoryid= {memoryid}')
            if i == 3:
                    print(f"Failed to generate a valid memory id after 3 attempts.")
                    return json.dumps({"role": "system", "content": f'No useful memories came back from this enquiry. '})
                            #### end of loop
                  
    def getmemorieslist(users_id):
        print(f'+++ getmemorieslist called for user {users_id}')
        rememberingagentquery=User.objects.filter(id=users_id)
        rememberingagentname=rememberingagentquery[0].username
        print(f'/// with name {rememberingagentname}')

        memoryquery = Memory.objects.filter(user=users_id)
        # print("/// memoryquery mmfn ", memoryquery)
        memories = []
        for memory in memoryquery:
            memorydict = {
                "memory_id": memory.id,
                "description": memory.description,
                "emotion": memory.emotion
            }
            # print(f'/// Memory: {memory}')
            memories.append(memorydict)
        # print("/// memorieslist  mfn ", memories)
        return memories
    
    def getmemorycontent(memory_id):
        print(f'+++ getmemorycontent called. id= {memory_id}')
                ####### check memory id is valid
        if not Memory.objects.filter(id=memory_id):
            print('.../// memory id not valid')
            return json.dumps({"role": "system", "content": f'No useful memories came back from this enquiry. '})
        memory = Memory.objects.get(id=memory_id)

        print(f'/// memory to be retrieved= {memory}')
        print(f'/// will return this= {memory.content}')
        return json.dumps(memory.content)

    def scopedfunctions(memorieslist, otheragentsdomainslist):
        print('+++ scopedfunctions called')
        result = [
                        {
                            "name": "getmemorycontent",
                            "description": f"If you need information look in this list of your personal memories, which shows their memory_id numbers: {memorieslist} . You can retrieve details about the memory  by calling this function. You can use  this new information to answer the question. Make sure you have the correct memory_id number ",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "memory_id": {
                                        "type": "integer",
                                        "description": "the id for the memory you want to retrieve",
                                    },
                                },
                                "required": ["memory_id"],
                            },
                        },
                        {"name": "askotheragent", "description": f"Only call this function if the user has asked for information you dont have. Here is a list of other agents and their domains of knowledge:{otheragentsdomainslist}. If one of them has information you need you can call the function,   giving the agentname  and the original users question as function parameters.  ",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "question": {
                                        "type": "string",
                                        "description": "the oringinal users question",
                                    }, "agentname": {"type": "string", "description": "the name of the agent you want to ask"},
                                },
                               "required": [ "agentname", "question"]  
                            },
                        },

                    ]   
        return result
   
    def otheragentdomainsfunction(userid):
        print('+++ otheragentdomainsfunction called')
        otheragentdomains = Domain.objects.all().exclude(user=userid)
        otheragentsdomainslist = []
        for domain in otheragentdomains:
            otheragentsdomainslist.append(
            {'agent': domain.user.username, 'domain': domain.domain})
        # print(f'>>> otheragentdomainlist {otheragentsdomainslist}')
        # print(f'>>> otheragentdomainlist type {type(otheragentsdomainslist)}')
        return otheragentsdomainslist
   
    def biographyitems(userobject):
        biographyitemsquery=Biographyitem.objects.filter(user=userobject)
        biographyitems = {}
        for item in biographyitemsquery:
            biographyitems[item.item]=item.description
        return biographyitems
    """
               the variables we need
    """
                ### create the selectedagent object
    
    userid = request.user.id
    # print(f">>>  username  {name} id {userid}")
    memory_id = 0
    print(f'memory_id {memory_id}')
                ##### make list of agents
    agentsquery = User.objects.all()
    agentslist = []
    for agent in agentsquery:
        # print('>>> agent type=', type(agent))
        agentslist.append(agent.username)
    print(">>> agentslist type ", type(agentslist))
    print(">>> agentslist ", agentslist)
    '''

                POST REQUEST

    '''
    if request.method == "POST":
        print('\n XXXXXXXXXXXXXXX POST request XXXXXXXXXXXXXXXXX \n')
        print('request=', request.POST)
        print(">>> request.session['selectedagent']= ", request.session['selectedagent'])
        name=request.session['selectedagent']
        print('>>>name= ',name)
        selectedagentobject = User.objects.get(username=name)
        
        biographyitems = biographyitems(selectedagentobject)
        print('||| biographyitems: ',biographyitems)
        print('||| biographyitems type: ',type(biographyitems))
        memorieslist = getmemorieslist(selectedagentobject.id)
        print('>>> memorieslist ', memorieslist)
        otheragentsdomainslist = otheragentdomainsfunction(userid)
        
        #### check if different agent selected  
        if 'selectagentsubmit' in request.POST:
            print('... Different agent selected')
            selectagentform = SelectAgentForm(request.POST, agentslist=agentslist)
            if selectagentform.is_valid():
                selectedagent = selectagentform.cleaned_data["agent"]
                print(f'... validform agentname= {selectedagent}')
                responseforuser = f"Hi there - my name's {selectedagent}, I just woke up"
                tokens = 0  
                if selectedagent != request.user.username :
                    print('>>> =', selectedagent, '>>> is not =', request.user.username)
                    request.session['selectedagent'] = selectedagent
                    print('>>> session[selectedagent] = ', request.session['selectedagent'])
                    name=selectedagent
                else:
                    request.session['selectedagent'] = 'request.user.username'
                    name= request.user.username
                messages.add_message(request, messages.INFO, f"Logged in as {request.user.username}")
                return render(
                        request,
                        "ayou/chat.html",
                        {
                            "chatform": NewChatForm(),
                            "responsecontent": responseforuser,
                            "tokensused": tokens,
                            "name": name,'selectagentform': SelectAgentForm(agentslist=agentslist),  
                        },
                    )
                
            # else:
            #     print('... selectagentform not valid')
            #     print(chatform.errors)
                


        elif 'chatsubmit' in request.POST:
            name=request.session['selectedagent']
            print('>>> name,  ', name)
            chatform = NewChatForm(request.POST)
            if chatform.is_valid():
                startnewchat = chatform.cleaned_data["startnewchat"]
                print("... startnewchat? ", startnewchat)
                ####### ensure there is a chat
                if not Chat.objects.filter(user=selectedagentobject.id).exists() or  startnewchat:
                    print('--- either startnewchat or no chat exists')
                   
                    thischat = Chat.objects.create(user=selectedagentobject)
                    print("... NEW thisChat > ", thischat)
                    messagechain = []
                    messagechain.append(systemmessage(name))
                    messagechain.append(exampleassistantmessage(name))
                    print("... newly created messagechain ", messagechain, type(messagechain))
                else:
                    print('--- there is a chat')
                    thischat = Chat.objects.filter(user=selectedagentobject).order_by("id").last()
                    # print("--- thischat/type ", thischat, type(thischat))
                    messagechain = thischat.messages
                    # print("--- messagechain/type ", messagechain, type(messagechain))

                            ####### add the user's message to the messagechain
                usercontent = chatform.cleaned_data["usercontent"]
                print("... usercontent ", usercontent)
                newusermessagedict = {"role": "user", "content": usercontent}            
                messagechain.append(newusermessagedict)
                # print("... messagechain at start   ", messagechain)
                
                            ####### now we have a messagechain with the user's message at the end
                
                            #######  get the openAI first completion
                
                functions = scopedfunctions(memorieslist, otheragentsdomainslist)

                firstcompletion = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=messagechain,
                max_tokens=200,
                temperature=1,
                functions=functions,
                function_call="auto",
                )   
                completionmessage = firstcompletion["choices"][0]["message"]
                print("... 1st completionmessage  type= ", type(completionmessage) )
                print("... 1st completionmessage  ",completionmessage, )
                """
                              #######  if functioncall in response , call it and append result to messagesforcompletion
                '"""
                if completionmessage.get("function_call"):
                    print("... function_call in completionmessage - will now call dealwithfunctionrequest()")
                    messagechain = dealwithfunctionrequest()
                    print("...now out of dealwithfunctionrequest())")
                    """

                              ####### make second primary agent call with function results

                    """
                    completionwithfunctionresults = openai.ChatCompletion.create(
                        model="gpt-3.5-turbo",
                    messages=messagechain,
                        max_tokens=200,
                    temperature=1,
                        functions=functions,
                        function_call="none",
                    )
                    # print("... 2nd completion> ", completionwithfunctionresults, type(completionwithfunctionresults))

                                ########  extract agent response from  secondcompletion
                    responseforuser = completionwithfunctionresults.choices[0].message["content"]
                    # print("... fn responseforuser> ", responseforuser,    type(responseforuser))

                                ########  make a dict of all the messages
                    secondresponsedict = completionwithfunctionresults.choices[0]['message']
                    # print(f'... fn responsedict type= {type(secondresponsedict)} ++++ {secondresponsedict}')
                    tokens = completionwithfunctionresults.usage.total_tokens
                    print("...> total_tokens ", tokens)
                    messagechain.append(secondresponsedict)

                else:
                    '''
                          #######     if no functioncall in response 
                    '''
                    print('---: no functioncalled')
                                ########  this goes to the html page later
                    responseforuser = firstcompletion.choices[0].message["content"]
                    # print("... responseforuser> ", responseforuser, type(responseforuser)   )


                                ########   this will be added to the chain
                    firstresponsedict = {'role': 'assistant', 'content': f'{firstcompletion.choices[0].message["content"]}'}    

                    tokens = firstcompletion.usage.total_tokens
                    print("--- total_tokens ", tokens)
                    messagechain.append(firstresponsedict)
                    # print("--- messagechain b4 save ", messagechain)

                # print('... messagechain b4 IF summary ', messagechain)

                """
                        #######        before saving, is the chain too long?
                """

                if tokens >3500:
                    print('...inside summary block')
                    summariserequestmessage = {"role": "system", "content": "IMPORTANT! summarise the  conversation so far, into one paragraph. Refer to the 'assistant' as 'I. You are the assistant."}
                    messagechain = messagechain[2:]
                    messagechain.append(summariserequestmessage)
                    # print('... toolong messagechain ', messagechain)

                    """
                                completion to summarise the chain 
                                loose the first 2 dicts in the chain!

                    """
                    summarycompletion = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=messagechain,
                    temperature=0.3
                    )
                    # print('... summarycompletion ', summarycompletion)
                    summarisedtokencount = summarycompletion.usage.total_tokens
                    print('... summarisedtokencount ', summarisedtokencount)

                    summarycompletioncontent = summarycompletion.choices[0].message
                    # print('... summarycompletioncontent ', summarycompletioncontent)
                    summarycompletionmessage = {"role": "assistant", "content": f"This is what you were talking about: {summarycompletioncontent}"}
                    messagechain = []
                    messagechain.append(systemmessage(name))
                    messagechain.append(exampleassistantmessage(name))
                    messagechain.append(summarycompletionmessage)
                    print('...> sumarised messagechain ', messagechain)
                    #       append the agent response and save the chat
                    # print('... messagechain after summaryblock ', messagechain)
                thischat.messages = messagechain
                thischat.save()

                """
                                    render the page with the last agent response
                """
                heading = figlettext('Chat with your Ayou clone', 'small')
                figletsubheading = figlettext('Chat with another Ayou clone', 'small')
                messages.add_message(request, messages.INFO, f"Logged in as {request.user.username}")
                return render(
                        request,
                        "ayou/chat.html",
                        {
                            "chatform": chatform,
                            "responsecontent": responseforuser,
                            "tokensused": tokens,
                            "name": name,'selectagentform': SelectAgentForm(agentslist=agentslist), 'agentslist': agentslist,
                             'heading': heading, 'figletsubheading': figletsubheading
                        },
                    )
            # else:
            #     return HttpResponse("FORM ERROR")
   
    """

            #######    GET REQUEST, render the page with an empty form

    """
    print('>>>> GET request')
    heading = figlettext('Chat with your Ayou clone', 'small')
    figletsubheading = figlettext('Chat with someone else', 'small')
    if 'selectedagent' not in request.session:
        request.session['selectedagent'] = request.user.username
    name = request.session['selectedagent']
    print('>>> reqest.session[selectedagent] ', request.session['selectedagent'])
    print('... name at GET ', name)
    messages.add_message(request, messages.INFO, f"{request.user.username}")

    return render(request, "ayou/chat.html", {"chatform": NewChatForm(), "name": 'your',"responsecontent": f"Hi, I'm {name}. I can tell you about myself and my past, or ask my friends for information",  'selectagentform': SelectAgentForm(agentslist=agentslist), 'agentslist': agentslist,  'heading': heading, 'figletsubheading': figletsubheading, 'pagebodyclass': 'chatbodyclass',  'pagemenuwideclass': 'chatmenuwideclass', 'pagelineheightclass':'chatlineheightclass', })




@login_required
def memories(request):
    message = ""
    try:
        domain = Domain.objects.get(user=request.user)
    except Domain.DoesNotExist:
        print('... no domain for this user' )
        domain = Domain.objects.create(user=request.user, domain='unspecified')
    

    heading = figlettext('Configure Ayou', 'small')
    

    def pagevariables(request, message):
        return  {"biographyitems": Biographyitem.objects.filter(user=request.user),    
                "memories": Memory.objects.filter(user=request.user),
                "chats": Chat.objects.filter(user=request.user),
                "newmemoryform": NewMemoryForm(),
                "deletememoryform": DeleteMemoryForm(),
                "deletebioform": DeleteBioForm(),
                'newbioform': NewBioForm(),
                'message': message,
                'domainslist': domainslist,
                'domainslistform': DomainsListForm(instance=domain),
                'heading': heading,
                'pagebodyclass': 'memoriesbodyclass',
                'pagemenuwideclass':'memoriesmenuwideclass',
                'pagelineheightclass':'memorieslineheightclass'}
    
    if Domain.objects.filter(user=request.user).exists():

        domainsquery = Domain.objects.filter(user=request.user)
        # print(f'... domainsquery  {domainsquery} type {type(domainsquery)}')
                # mylist
        domainslist=[]
        # print(f'... domainslist 1 {domainslist} type {type(domainslist)}')
        for domain in domainsquery:
            # print(f'... domain.domain {domain.domain} type {type(domain.domain)}')  
            domainslist.append(domain.domain)   
        # print(f'... domainslist 2 {domainslist} type {type(domainslist[0])}')
        #         #endmylist
        
    if request.method == "POST":
        print(">>> POST request ", request.POST)
        print('>>> POST request content>', request.POST)
        """
            make a function for these is_valid() checks
    
        """
        if request.POST.get("formname") == "newbioform":
            print(">>> nnewbioform request")
            newbioform = NewBioForm(request.POST)
            if newbioform.is_valid():
                print(">>> newbioform is valid ")
                
                item = newbioform.cleaned_data['item']
                print('... item ', item)
                description = newbioform.cleaned_data['description']
                print('... description ', description)  
                newbio = Biographyitem.objects.create(item=item, description=description, user=request.user)
                print('... newbio ', newbio)    
                newbio.save()
                message = f"New biography item added: {description}"
                print('... newbio in db', Biographyitem.objects.filter(user=request.user).order_by('id').last())
            else:
                print('... newbioform not valid', newbioform.errors)
                message = "Biography item not added. Correct the form and try again."
                return render(request, "ayou/memories.html", pagevariables(request, message))
            
        elif request.POST.get("formname") == "deletebioform":
            deletebioform = DeleteBioForm(request.POST)
            if deletebioform.is_valid():
                print(">> deletebioform  valid ")
                deletebioboo = deletebioform.cleaned_data["deletebioboo"]
                if deletebioboo:
                    bioid = request.POST.get("id")  
                    # print('... bioid ', bioid)
                    biotodelete = Biographyitem.objects.get(id=bioid)
                    # print('... biotodelete ', biotodelete)
                    message = f"Biography item deleted: {biotodelete.item}"
                    biotodelete.delete()
                    # print('... biotodelete deleteed now render page')
            else:
                # print('... deletebioform not valid', deletebioform.errors)
                message = "Biography item not deleted. Correct the form and try again."
                return render(request, "ayou/memories.html", pagevariables(request, message))
            
        elif request.POST.get("formname") == "newmemoryform":
            newmemoryform = NewMemoryForm(request.POST)
            if newmemoryform.is_valid():
                date = newmemoryform.cleaned_data['date']
                description = newmemoryform.cleaned_data['description']
                content = newmemoryform.cleaned_data['content']
                emotion = newmemoryform.cleaned_data['emotion']
                newmemory = Memory.objects.create(date=date, description=description, content=content, emotion=emotion, user=request.user)
                newmemory.save()
                message = f"New memory added: {description}"
                # print('... newmemory ', newmemory)
                # print('... newmemoryfromdb ', Memory.objects.order_by('id').last())
            else:
                # print('... newmemoryform not valid', newmemoryform.errors)
                message = "Memory not added. Correct the form and try again."
                return render(request, "ayou/memories.html", pagevariables(request, message))
            
        elif request.POST.get("formname") == "deletememoryform":
            deletememoryform = DeleteMemoryForm(request.POST)
            if deletememoryform.is_valid():
                deletememoryboo = deletememoryform.cleaned_data["deletememoryboo"]
                if deletememoryboo:
                    # print(">>> boolean deletememory ", request.POST.get("deletememory"))
                    # print(">>> memoryid ", request.POST.get("memory_id"))
                    memoryid = request.POST.get("id")
                    memorytodelete = Memory.objects.get(id=memoryid)
                    message = f"Memory deleted: {memorytodelete.description}"
                    memorytodelete.delete()
                    # print(">>> memory deleted")

        if request.POST.get("formname") == "domainslistform":
            # print('... found form in POST')
            domainslistform = DomainsListForm(request.POST, instance=domain)
            if domainslistform.is_valid():
                domainslistform.save()
                print('updated domain? ',Domain.objects.get(user=request.user))
                message='knowledge area updated'

        print('rendering')     
        
        messages.add_message(request, messages.INFO, f" {request.user.username}")
        return render(request, "ayou/memories.html", pagevariables(request, message))
    """
                if here by GET
    """
    print('request path ', request.path)
    
  
    
    messages.add_message(request, messages.INFO, f" {request.user.username}")
    return render(request, "ayou/memories.html", pagevariables(request, message), )
 
