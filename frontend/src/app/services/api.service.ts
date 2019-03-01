
import {throwError as observableThrowError,  Subject ,  Observable , of } from 'rxjs';
import { Injectable } from '@angular/core';
import { HttpClient, HttpResponse, HttpErrorResponse, HttpHeaders } from '@angular/common/http';
import { Router } from '@angular/router';

import { catchError, map, tap, share } from 'rxjs/operators';

import { CookieService } from './cookie.service';


// refer to feedback_tool/views/auth.py:login
export class UserData {
  displayName: string;
  title: string;  // e.g. Software Developer
  principals: [string];
  businessUnit: string;
}

export class LoginSuccessPayload {
  success: boolean;
  data: UserData;
}

// refer to feedback_tool/views/nomination.py
export class MessageTemplatePayload {
  heading: string;
  body: string;
  buttonText: string;
  buttonLink: string;
  canNominate: boolean;
}

export class NomineeItem {
  displayName: string;
  username: string;
  hasExistingFeedback: string;
  position: string;
  managerDisplayName: string;
  department: string;
}

export class NomineePayload {
  period: string;
  nominees: NomineeItem[];
}

// refer to feedback_tool/views/feedback.py
export class FeedbackFormItem {
  questionId: string;
  question: string;
  caption?: string;
  rawAnswer?: string;
  answerId?: string;
  answer?: string;
}
export class GiveFeedbackPayload {
  form: FeedbackForm;
}

export class FeedbackForm {
  items: FeedbackFormItem[];
  employee: {
    displayName: string,
    position: string
  };
  periodName: string;
  readOnly?: boolean;
  endDate: string;
}

export class FeedbackHistoryPayload {
  feedback: {
    displayName: string,
    items: [
      {
        periodDescription: string,
        enable: boolean,
        items: [{
          question: string,
          answer: string
        }]
      }
    ]
  };
}

// refer to feedback_tool/views/manager.py
export class StatsPayload {
  stats: {
    periods: [string],
    periodColumns: [string],
    values: [any]
  };
}

export class SummaryFeedbackPayload {
  summary: FeedbackForm;
}

// refer to feedback_tool/views/external.py
export class ExternalFeedbackStatusPayload {
  canInvite: boolean;
  heading?: string;
  body?: string;
  invitees?: [Invitee];
}

export class Invitee {
  displayName: string;
  email: string;
  businessUnit: string;
  department: string;
}

// refer to feedback_tool/views/metadata.py
export class MetadataPayload {
  metadata: Metadata;
}

export class Metadata {
  businessUnit: string;
  companyName: string;
  loginPasswordMessage: string;
  loginUsernameMessage: string;
  passwordlessAccess: boolean;
  supportEmail: string;
}

export class TalentManagerPanelData {
  userCount: number;
  generatePopulationMsg: string;
  uploadNewPopulationMsg: string;
}

// refer to feedback_tool/views/talent_manager.py
export class CSVUploadStatusPayload {
  messages: [string];
}

@Injectable()
export class ApiService {

  rootUrl = '/api/v1';
  redirectUrl: string;
  isInitializing = true;
  private _userData: Observable<UserData>;
  private _metadata: MetadataPayload;
  private _metadataObservable: Observable<MetadataPayload>;

  private errorSource = new Subject<HttpErrorResponse>();
  error$ = this.errorSource.asObservable();
  constructor(private http: HttpClient, private cookie: CookieService, private router: Router) {
  }

  getUserData(): Observable<UserData> {
    return this.http.get(this.rootUrl + '/user-data', { withCredentials: true })
      .pipe(
        map((res: LoginSuccessPayload) => res.data)
      );
  }

  login(username, password): Observable<boolean> {
    const headers = new HttpHeaders({ 'Content-Type': 'application/x-www-form-urlencoded' });
    return this.http.post(this.rootUrl + '/login', { username, password }, { headers, withCredentials: true })
      .pipe(
        map(
          (res: LoginSuccessPayload) => {
            this._userData = of(res.data);
            return true;
          })
      );
  }

  fetchTemplate(endpoint: string): Observable<{} | MessageTemplatePayload> {
    return this._httpWrapper(this.http.get(this.rootUrl + endpoint, { withCredentials: true })
      .pipe(map((res: MessageTemplatePayload) => res)));
  }

  getMetadata(): Observable<MetadataPayload> {
    if (this._metadata) {
      return of(this._metadata);
    } else if (this._metadataObservable) {
      return this._metadataObservable;
    } else {
      this._metadataObservable = this.http.get(this.rootUrl + '/metadata',
        { observe: 'response', withCredentials: true })
        .pipe(
          map((response: HttpResponse<MetadataPayload>) => {
            this._metadataObservable = null;
            if (response.status === 400) {
              return new MetadataPayload();
            } else if (response.status === 200) {
              this._metadata = response.body;
              return this._metadata;
            }
          }),
          share()
        );

      return this._metadataObservable;
    }
  }

  selfNominate(): Observable<{} | MessageTemplatePayload> {
    return this._httpWrapper(this.http.post(this.rootUrl + '/self-nominate', {}, { withCredentials: true })
      .pipe(map((res: MessageTemplatePayload) => res)));
  }

  getNominees(): Observable<{} | NomineePayload | MessageTemplatePayload> {
    return this._httpWrapper(this.http.get(this.rootUrl + '/nominees', { withCredentials: true })
      .pipe(map((res: NomineePayload | MessageTemplatePayload) => res)));
  }

  getFeedbackAboutMe(): Observable<{} | FeedbackHistoryPayload> {
    return this._httpWrapper(this.http.get(this.rootUrl + `/feedback-about-me`, { withCredentials: true })
      .pipe(map((res: FeedbackHistoryPayload) => res)));
  }

  getFeedbackForm(username: String): Observable<{} | GiveFeedbackPayload> {
    return this._httpWrapper(this.http.get(this.rootUrl + `/feedback/${username}/`, { withCredentials: true })
      .pipe(map((res: GiveFeedbackPayload) => res)));
  }

  getFeedbackHistory(username: String): Observable<{} | FeedbackHistoryPayload> {
    return this._httpWrapper(this.http.get(this.rootUrl + `/feedback-history/${username}/`, { withCredentials: true })
      .pipe(map((res: GiveFeedbackPayload) => res)));
  }

  putFeedbackForm(username: String, formItems: FeedbackFormItem[]): Observable<object> {
    return this._httpWrapper(this.http.put(this.rootUrl + `/feedback/${username}/`, { form: formItems }, { withCredentials: true })
      .pipe(map((res: object) => res)));
  }

  getTeamStats(): Observable<{} | StatsPayload> {
    return this._httpWrapper(this.http.get(this.rootUrl + `/team-stats`, { withCredentials: true })
      .pipe(map((res: StatsPayload) => res)));
  }

  getCompanyStats(): Observable<{} | StatsPayload> {
    return this._httpWrapper(this.http.get(this.rootUrl + `/company-stats`, { withCredentials: true })
      .pipe(map((res: StatsPayload) => res)));
  }

  getSummaryFeedback(username: String): Observable<{}| SummaryFeedbackPayload> {
    return this._httpWrapper(this.http.get(this.rootUrl + `/summarise/${username}/`, { withCredentials: true })
      .pipe(map((res: SummaryFeedbackPayload) => res)));
  }

  putSummaryFeedback(username: String, formItems: FeedbackFormItem[]): Observable<object> {
    return this._httpWrapper(this.http.put(this.rootUrl + `/summarise/${username}/`, { form: formItems }, { withCredentials: true })
      .pipe(map((res: object) => res)));
  }

  sendEmail(templateKey: String): Observable<object> {
    return this._httpWrapper(this.http.post(this.rootUrl + `/send-email`, { templateKey }, { withCredentials: true })
      .pipe(map((res: object) => res)));
  }

  getExternalInviteStatus(): Observable<{}| ExternalFeedbackStatusPayload> {
    return this._httpWrapper(this.http.get(this.rootUrl + `/external-invite`, { withCredentials: true })
      .pipe(map((res: ExternalFeedbackStatusPayload) => res)));
  }

  sendExternalInvite(email: String): Observable<object> {
    return this.http.post(this.rootUrl + `/external-invite`, { email }, { withCredentials: true })
      .pipe(
        map((res: object) => res),
        catchError((err) => {
          if (err.error === undefined || err.error === null) {
            this.errorSource.next(err);
          }
          throw err;
        })
      );
  }

  uploadNewPopulationCSV(base64Contents: string): Observable<CSVUploadStatusPayload> {
    return this.http.post(this.rootUrl + `/upload-new-population-csv`, { 'content': base64Contents }, { withCredentials: true })
      .pipe(
        map((res: CSVUploadStatusPayload) => res),
        catchError((err) => {
          return observableThrowError(
            new Error(`Upload failed with the following error: ${ err.status } ${ err.statusText }`)
          );
        })
      );
  }

  generatePopulationCSV(businessUnit: string): Observable<string> {
    return this.http.get(this.rootUrl + `/generate-population.csv?businessUnit=${encodeURIComponent(businessUnit)}`, {responseType: 'text'})
    .pipe(
      tap( 
        data => data,
        error => error
      )
    );
  }

  getTalentManagerPageData(): Observable<TalentManagerPanelData> {
    return this.http.get(this.rootUrl + '/talent-manager-page-data')
      .pipe(
        map((res: TalentManagerPanelData) => res)
      );
  }

  getCurrentPopulationCSV(): Observable<string> {
    return this.http.get(this.rootUrl + '/get-current-population.csv', {responseType: 'text'})
    .pipe(
      tap( 
        data => data,
        error => error
      )
    );
  }

  _httpWrapper(httpObs: Observable<object>) {
    return httpObs
      .pipe(
        catchError((err) => {
          this.errorSource.next(err);
          throw err;
        })
      );
  }

  logout(event): void {
    event.preventDefault();
    this.http.post(this.rootUrl + '/logout', { withCredentials: true }).subscribe(() => {
      this.router.navigate(['/login'], {queryParams: {logoutSuccess: true}});
    }, (error) => {
      console.log(error);
      this.router.navigate(['/login'], {queryParams: {logoutSuccess: false}});
    });
  }
}
