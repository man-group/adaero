import { BrowserModule } from '@angular/platform-browser';
import { LOCALE_ID, NgModule } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { HttpClientModule, HttpClientXsrfModule } from '@angular/common/http';

import { NgbModule } from '@ng-bootstrap/ng-bootstrap';

import { AppComponent } from './app.component';

import {
  GiveFeedbackComponent,
  NomineesListComponent,
  LoginComponent,
  SelfNominateComponent,
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
import { NomineeFilterPipe } from './pipes/nominee-filter.pipe';
import { ModalComponent } from './components/widgets/modal/modal.component';
import { AuthenticatedComponent } from './components/views/authenticated/authenticated.component';
import { FeedbackHistoryComponent } from './components/widgets/feedback-history/feedback-history.component';
import { FeedbackHistoryViewComponent } from './components/views/feedback-history-view/feedback-history-view.component';
import { ExternalInviteComponent } from './components/views/external-invite/external-invite.component';

@NgModule({
  declarations: [
    // views
    AppComponent,
    LoginComponent,
    AuthenticatedComponent,
    GiveFeedbackComponent,
    NomineesListComponent,
    SelfNominateComponent,
    StatsComponent,
    SummariseFeedbackComponent,
    FeedbackAboutMeComponent,
    TalentManagerPanelComponent,
    FeedbackHistoryViewComponent,
    ExternalInviteComponent,

    // components
    FeedbackFormComponent,
    ModalComponent,
    FeedbackHistoryComponent,

    // pipes
    NomineeFilterPipe,



  ],
  entryComponents: [
    ModalComponent,
  ],
  imports: [
    BrowserModule,
    HttpClientModule,
    HttpClientXsrfModule,
    FormsModule,
    NgbModule.forRoot(),
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
