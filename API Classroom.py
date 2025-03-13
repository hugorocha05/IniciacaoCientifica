import os
import io
import requests
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = [
    "https://www.googleapis.com/auth/classroom.courses.readonly",
    "https://www.googleapis.com/auth/classroom.rosters.readonly",
    "https://www.googleapis.com/auth/classroom.profile.emails",
    "https://www.googleapis.com/auth/classroom.student-submissions.students.readonly",
    "https://www.googleapis.com/auth/drive.readonly"
]

def extract_prefix(s):
    parts = s.split('@')
    return parts[0]

def get_classroom_id(courses):
    ids = []
    for i in range(len(courses)):
        ids.append(courses[i]['id'])
        print(f"{i} - {courses[i]['name']} - {courses[i]['id']}")

    index = int(input("Digite o número da posição da classe desejada: "))
    return ids[index]

def get_classwork_id(assignments):
    ids = []
    for i in range(len(assignments['courseWork'])):
        ids.append(assignments['courseWork'][i]['id'])
        print(f"{i} - {assignments['courseWork'][i]['title']} - {assignments['courseWork'][i]['id']}")

    index = int(input("Digite o número da posição da atividade desejada: "))
    return ids[index]

def formatação(classroom_service, classroom_id, submissions, drive_service):
    folder_path = 'Submissions'
    open("ErroFormatação.txt", "w")

    for submission in submissions.get('studentSubmissions', []):
        student_id = submission['userId']
        student = classroom_service.courses().students().get(courseId=classroom_id, userId=student_id).execute()

        student_name = student['profile']['name']['fullName']
        student_email = student['profile']['emailAddress']
        student_login = extract_prefix(student_email)
        late = submission.get('late', False)
        attachments = submission.get('assignmentSubmission', {}).get('attachments', [])

        if not attachments:
            missing = True
        else:
            missing = False

        print("Student Name:", student_name)
        print("Student Email:", student_email)
        print("Student Login:", student_login)
        print("Late:", late)
        print("Missing:", missing)

        with open("ErroFormatação.txt", "a") as file:
            print("Attachments:")
            if attachments:
                if len(attachments) > 1:
                    file.write(f"{student_name} ({student_login}):\n\tEntregou mais de um arquivo\n\n")
                else:
                    for attachment in attachments:
                        drive_file = attachment.get('driveFile')
                        if drive_file:
                            file_id = drive_file.get('id')
                            file_name = drive_file.get('title', 'No file name')
                            print("  File Name:", file_name)

                            if '.zip' not in file_name:
                                file.write(f"{student_name} ({student_login}):\n\tNão entregou .zip\n\n")
                            
                            elif file_name != student_login + '.zip':
                                file.write(f"{student_name} ({student_login}):\n\tArquivo com nome errado\n\tNome original: {file_name}\n\tNome corrigido: {student_login + '.zip'}\n\n")
                                file_name = student_login + '.zip'

                            # Attempt to download the file
                            try:
                                download_file(drive_service, file_id, file_name, folder_path)
                            except:
                                print(f"Error downloading {file_name}")
                                file.write(f"{student_name} ({student_login}):\n\tErro de download\n\tPor favor apagar {file_name}\n\n")
                                # Apagar automaticamente o arquivo errado

            else:
                print("  No attachments found")
                file.write(f"{student_name} ({student_login}):\n\tNenhum arquivo encontrado\n\n")
            print()

def download_file(service, file_id, file_name, folder_path):
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    
    file_path = os.path.join(folder_path, file_name)
    
    request = service.files().get_media(fileId=file_id)
    fh = io.FileIO(file_path, 'wb')
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
    print(f"Downloaded {file_name} to {folder_path}")

def main():
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    try:
        classroom_service = build("classroom", "v1", credentials=creds)
        drive_service = build("drive", "v3", credentials=creds)


        results = classroom_service.courses().list().execute()

        courses = results.get("courses", [])
        classroom_id = get_classroom_id(courses)
        print()

        assignments = classroom_service.courses().courseWork().list(courseId=classroom_id).execute()
        coursework_id = get_classwork_id(assignments)
        submissions = classroom_service.courses().courseWork().studentSubmissions().list(courseId=classroom_id, courseWorkId=coursework_id).execute()
        print()

        formatação(classroom_service, classroom_id, submissions, drive_service)
          
    except HttpError as error:
        if error.resp.status == 404:
            print("Course not found. Please check if the provided classroom ID is correct.")
        else:
            print(f"An error occurred: {error}")

    print("DONE")

if __name__ == "__main__":
    main()
