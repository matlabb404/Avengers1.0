Working with whole app and not first running (REACT FRONTEND AND FASTAPI BACKEND)
---------------------------------------------------------------------------------

1. Activate your virtual environment. [ env/scripts/activate ]

2. Navigate to your APIs folder(your backend).

3. Run your backend hosting at 0.0.0.0 and on port 8000. [ uvicorn main:app --host 0.0.0.0 --port 8000 ]
if you are not editing backend and [ uvicorn main:app --host 0.0.0.0 --port 8000 --reload ] if you are 
editing backend.

4. Navigate to your patterns folder(your frontend).

5. Run your frontend. [ npm start ]

6. Open your actions folder and edit all urls to the backend, replace them with your current IP which depends on the 
network you are on currently, you can find this in your terminal after running npm start on the line metro waiting. 

[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[

Starting project at C:\Users\USER\Desktop\aveng\Avengers1.0\patterns
Starting Metro Bundler
▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄
█ ▄▄▄▄▄ █▄▄████ █▀█ ▄▄▄▄▄ █
█ █   █ █ ▀█ ▄ ▄▀ █ █   █ █
█ █▄▄▄█ █▄ ▄▄▀█▀▄▀█ █▄▄▄█ █
█▄▄▄▄▄▄▄█▄▀▄▀▄█▄▀ █▄▄▄▄▄▄▄█
█▄▄▄ ▀█▄█ ▀███▀▀▄▄▄██▄ ▄▀▄█
██▀ █▄▀▄  ██▀▀ ▄█▀█ ▀██▀███
██▀ ▀▀▀▄▄ ▄▀ █ █▀▄█ ▄ █ █▀█
█▀▄▀█▀▀▄▀ ▀ █ ▄██ ▀▀█▀▀█ ▀█
████▄██▄█▀▄ ▄▀  ▄ ▄▄▄ ▀▄█▀█
█ ▄▄▄▄▄ ████▄ █▀█ █▄█ █▄ ▄█
█ █   █ █▀ ▄▄▀▀▀▀▄▄   █▀▀ █
█ █▄▄▄█ █ █ ▄▄▀▄▀▄▀▄█▄▄ ▄██
█▄▄▄▄▄▄▄█▄█▄██▄█▄██████▄▄▄█

› Metro waiting on exp://'''''''''192.168.8.117''''''''':8081 
› Scan the QR code above with Expo Go (Android) or the
Camera app (iOS)

]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]

CORRECTIONS MOVE FROM 

>>>>>>>>>>>>>>> const response = await fetch('http://192.168.8.104:8000/Account/Login', config); //my OLD IP

>>>>>>>>>>>>>>> const response = await fetch('http://192.168.8.117:8000/Account/Login', config); //my NEW IP




------------------------------------------------------------------------------------------------------------




____________________________________________________________________________________________________________


Working with just FASTAPI(FASTAPI BACKEND)
---------------------------------------------------------------------------------

1. Navigate to your account_module.py. [ Avengers1.0\APIs\app\modules\account_module.py ]

2. Edit the ''''''''''''login_for_access_token()'''''''''''''' function from this 

[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[

def login_for_access_token(db: Session, form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    if form_data.email:
        user = user_login(form_data.email, form_data.password, db)
    else:
        user = user_login(form_data.username, form_data.password, db)
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(user.email, expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer"}

]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]

to look like.

[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[

def login_for_access_token(db: Session, form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    #if form_data.email:
    #   user = user_login(form_data.email, form_data.password, db)
    #else:
    user = user_login(form_data.username, form_data.password, db)
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(user.email, expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer"}

]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]


3. Run your backend. [ uvicorn main:app --reload ]


____________________________________________________________________________________________________________

NB: Edit the readme  if necessary and abeg warn us before your push :/
____________________________________________________________________________________________________________

                         oooo$$$$$$$$$$$$oooo
                      oo$$$$$$$$$$$$$$$$$$$$$$$$o
                   oo$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$o         o$   $$ o$
   o $ oo        o$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$o       $$ $$ $$o$
oo $ $ "$      o$$$$$$$$$    $$$$$$$$$$$$$    $$$$$$$$$o       $$$o$$o$
"$$$$$$o$     o$$$$$$$$$      $$$$$$$$$$$      $$$$$$$$$$o    $$$$$$$$
  $$$$$$$    $$$$$$$$$$$      $$$$$$$$$$$      $$$$$$$$$$$$$$$$$$$$$$$
  $$$$$$$$$$$$$$$$$$$$$$$    $$$$$$$$$$$$$    $$$$$$$$$$$$$$  """$$$
   "$$$""""$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$     "$$$
    $$$   o$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$     "$$$o
   o$$"   $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$       $$$o
   $$$    $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$" "$$$$$$ooooo$$$$o
  o$$$oooo$$$$$  $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$   o$$$$$$$$$$$$$$$$$
  $$$$$$$$"$$$$   $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$     $$$$""""""""
 """"       $$$$    "$$$$$$$$$$$$$$$$$$$$$$$$$$$$"      o$$$
            "$$$o     """$$$$$$$$$$$$$$$$$$"$$"         $$$
              $$$o          "$$""$$$$$$""""           o$$$
               $$$$o                 oo             o$$$"
                "$$$$o      o$$$$$$o"$$$$o        o$$$$
                  "$$$$$oo     ""$$$$o$$$$$o   o$$$$""  
                     ""$$$$$oooo  "$$$o$$$$$$$$$"""
                        ""$$$$$$$oo $$$$$$$$$$       
                                """"$$$$$$$$$$$        
                                    $$$$$$$$$$$$       
                                     $$$$$$$$$$"      
                                      "$$$""""

                                                          