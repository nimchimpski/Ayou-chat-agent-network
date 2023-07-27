from django.shortcuts import render
from django.contrib.auth import authenticate, login, logout
from django import forms
from django.http import HttpResponseRedirect, HttpResponse
from django.urls import reverse
import requests, os, openai
# from dotenv import load_dotenv
# from .models import Memory, Biographyitem, Chat


class NewLoginForm(forms.Form):
    username = forms.CharField(label='username')
    password = forms.CharField(label='password')
 

class NewChatForm(forms.Form):
    startnewchat = forms.BooleanField(label="New topic?", required=False)
    usercontent = forms.CharField(label='What do you want to say?')

# load_dotenv()
# openai.api_key = os.getenv("OPENAI_API_KEY")
openai.api_key = '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'

namequery = Biographyitem.objects.get(item='firstname')


memoryquery = Memory.objects.all()

print('>>> memoryquery ', memoryquery)
memories = []
for memory in memoryquery:
    memories.append(memory.description)
print('>>>memories ', memories)




# Create your views here.

def index(request):
    if not request.user.is_authenticated:
        return HttpResponseRedirect(reverse('ayou:login'))
    name = request.user.username
    print('### user ', request.user.username)
    return render(request, 'ayou/chat.html', {'form': NewLoginForm()})

def login_view(request):
    if request.method == 'POST':
        print('>>> POST')
        form = NewLoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            print('>>> username ', username)
            user = authenticate(request, username=username, password=password)
            if user:
                login(request, user)
                return HttpResponseRedirect(reverse('ayou:chat'))
            else:
                return render(request, 'ayou/index.html', {'message':'Invalid credentials'})
    form = NewLoginForm()
    if not request.user.is_authenticated:
        print('>>> not loged in')
        return render(request, 'ayou/index.html', {'form': NewLoginForm()})
        

        # return HttpResponseRedirect(reverse('ayou:login'))
    
    # return render(request, 'ayou/index.html', {'form': NewLoginForm()})  
    return HttpResponseRedirect(reverse('ayou:chat'))

def logout_view(request):
    logout(request)
    message='Logged out'
    return HttpResponseRedirect(reverse('ayou:login'))

def chat(request):
    
    if request.method == 'POST':
        form = NewChatForm(request.POST)

        # print('>>> ', name)
        if form.is_valid():
            startnewchat = form.cleaned_data['startnewchat']
            print('>>> startnewchat? ', startnewchat)
            # ensure there is a chat
            if not Chat.objects.all() or startnewchat:
                thischat = Chat.objects.create()
                print('>>> new thisChat> ', thischat)
            print('>>> num chats  ', Chat.objects.count())
            usercontent = form.cleaned_data['usercontent']
            thischat = Chat.objects.order_by('id').last()
            print('>>> thischat.id ', thischat.id)
            print('>>> thischat msgs>>>type ', thischat.messages, type(thischat.messages))
            # create new message dict with form data
            newusermessagedict = {'role':'user', 'content': usercontent}
            print('>>> newusermessagedict ', newusermessagedict)
            # append the newusermessagedict to the stored message list
            # get the existing messages list/create it,  and append newmessage
            allmessages = thischat.messages or []
            allmessages.append(newusermessagedict)
            allmessages
            print('>>> thischat.messages ', thischat.messages, type(thischat.messages))
            print('>>> allmessages type  ', type(allmessages))
            print('>>> allmessages ', allmessages)
            # add system message
            name = request.user.username
            systemprompt = f'Reply in the style of a serious character, and introduce yourself as the digital version of  {name}. Keep your answers to no more than 2 sentences. You might be a Replicant from Bladerunner - whho knows! These are your personal memories: {memories}. Only mention them if you are spcifically asked to remember, but if you do, ask if they want to see a picture of your memory'
            systemmessage = {'role':'system', 'content': systemprompt}
            messagesforcompletion = allmessages.copy()
            messagesforcompletion.append(systemmessage)
            print('>>> asystemmessage ', systemmessage)
            # define the functions
            functions = [
            {
            "name": "getmemories",
            "description": "Get memories from db",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The city and state, e.g. San Francisco, CA",
                    },
                    "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
                },
                "required": ["location"],
            },
            }
            ]

            # get the openAI response
            completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo", messages = messagesforcompletion, max_tokens = 200, temperature=1, functions=functions, function_call='auto')
            print('>>> completion> ', completion)

            responsecontent = completion.choices[0].message['content']
            tokens = completion.usage.total_tokens
                

            print('>>> total_tokens ', tokens)
            responsedict = completion.choices[0].message
            print('>>> responsedict> ', responsedict, type(responsedict))
            print('>>> responsecontent> ', responsecontent, type(responsecontent))
            # append the AI response and save
            allmessages.append(responsedict)
            print('>>> allmessages b4 save ', allmessages)
            thischat.messages = allmessages
            thischat.save()
            # look up a memory

            name = request.user.username
            return render(request, 'ayou/chat.html', {'form': form, 'responsecontent': responsecontent, 'tokensused': tokens, 'firstname': name})
        else:
            return HttpResponse('FORM ERROR')
    name = request.user.username
    return render(request, 'ayou/chat.html', {'form': NewChatForm(), 'firstname': name })

def social(request):
    return render(request, 'ayou/social.html')

def diary(request):
    return render(request, 'ayou/diary.html')

def account(request):
    return render(request, 'ayou/account.html')

def memories(request):

  

    return render(request, 'ayou/memories.html', {'memories': Memory.objects.all(), 'chats': Chat.objects.all(), })
    # return HttpResponse('learn')