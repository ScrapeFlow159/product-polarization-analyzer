on backend apply following:
cd backend
venv\Scripts\activate
uvicorn main:app --reload
after this if the requirements or libraries are not installed type this..
pip install -r requirements.txt
then on frontend add following:
python -m http.server 5500
