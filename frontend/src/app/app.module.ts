import { BrowserModule } from '@angular/platform-browser';
import { LOCALE_ID, NgModule } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { HttpClientModule, HttpClientXsrfModule } from '@angular/common/http';

import { NgbModule } from '@ng-bootstrap/ng-bootstrap';

import { AppComponent } from './app.component';

import {
  GiveFeedbackComponent,
  EnrolleesListComponent,
  LoginComponent,
  EnrolComponent,
  StatsComponent,
  SummariseFeedbackComponent,
  FeedbackAboutMeComponent,
  TalentManagerPanelComponent,
} from './components/views';

import {
  FeedbackFormComponent,
} from './components/widgets/';

import { AppRoutingModule } from './app-routing.module';

import { ApiService } from './services/api.service';
import { CookieService } from './services/cookie.service';
import { AuthGuardService, AnonGuardService, PendingChangesGuardService } from './guards';
import { EnrolleeFilterPipe } from './pipes/enrollee-filter.pipe';
import { ModalComponent } from './components/widgets/modal/modal.component';
import { AuthenticatedComponent } from './components/views/authenticated/authenticated.component';
import { FeedbackHistoryComponent } from './components/widgets/feedback-history/feedback-history.component';
import { FeedbackHistoryViewComponent } from './components/views/feedback-history-view/feedback-history-view.component';
import { RequestComponent } from './components/views/request/request.component';

@NgModule({
  declarations: [
    // views
    AppComponent,
    LoginComponent,
    AuthenticatedComponent,
    GiveFeedbackComponent,
    EnrolleesListComponent,
    EnrolComponent,
    StatsComponent,
    SummariseFeedbackComponent,
    FeedbackAboutMeComponent,
    TalentManagerPanelComponent,
    FeedbackHistoryViewComponent,
    RequestComponent,

    // components
    FeedbackFormComponent,
    ModalComponent,
    FeedbackHistoryComponent,

    // pipes
    EnrolleeFilterPipe,



  ],
  entryComponents: [
    ModalComponent,
  ],
  imports: [
    BrowserModule,
    HttpClientModule,
    HttpClientXsrfModule,
    FormsModule,
    NgbModule,
    // local modules
    AppRoutingModule,
  ],
  providers: [
    ApiService,
    AnonGuardService,
    AuthGuardService,
    PendingChangesGuardService,
    CookieService,
    { provide: LOCALE_ID, useValue: 'en'}
  ],
  bootstrap: [AppComponent]
})
export class AppModule { }
