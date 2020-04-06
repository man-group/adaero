import { BrowserModule } from '@angular/platform-browser';
import { LOCALE_ID, NgModule } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { HttpClientModule, HttpClientXsrfModule } from '@angular/common/http';

import { NgbModule } from '@ng-bootstrap/ng-bootstrap';

import { AppComponent } from './app.component';

import {
  AuthenticatedComponent,
  EnrolComponent,
  FeedbackAboutMeComponent,
  EnrolleesListComponent,
  FeedbackHistoryViewComponent,
  GiveFeedbackComponent,
  LoginComponent,
  RequestComponent,
  StatsComponent,
  SummariseFeedbackComponent,
  TalentManagerPanelComponent,
} from './components/views';

import {
  FeedbackFormComponent,
  FeedbackUserListComponent,
  FeedbackHistoryComponent,
  ModalComponent,
  NgbdSortableHeader,
} from './components/widgets/';

import { AppRoutingModule } from './app-routing.module';

import { ApiService } from './services/api.service';
import { CookieService } from './services/cookie.service';
import { AuthGuardService, AnonGuardService, PendingChangesGuardService } from './guards';
import { EnrolleeFilterPipe } from './pipes/enrollee-filter.pipe';

@NgModule({
  declarations: [
    // views
    AppComponent,
    LoginComponent,
    AuthenticatedComponent,
    GiveFeedbackComponent,
    EnrolleesListComponent,
    EnrolComponent,
    NgbdSortableHeader,
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

    FeedbackUserListComponent,



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
