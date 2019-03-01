import { Component, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { ApiService, FeedbackHistoryPayload } from '../../../services/api.service';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';

@Component({
  selector: 'app-feedback-history-view',
  templateUrl: './feedback-history-view.component.html',
  styleUrls: ['./feedback-history-view.component.scss']
})
export class FeedbackHistoryViewComponent implements OnInit {

  data: FeedbackHistoryPayload;
  readonly description = [`Find below a history of their feedback summaries. Colleagues were given the opportunity to provide feedback. \
    You or a previous line manager then reviewed the feedback and provided the summaries presented below.`,
    `Managers can view historical feedback about their Direct Reports spanning the last three feedback cycles. \
    Staff can see their full history of feedback.`];

  constructor(public api: ApiService, private route: ActivatedRoute) { }

  title(): string {
    if (this.data) {
      return `Feedback about ${this.data.feedback.displayName}`;
    }
  }

  ngOnInit() {
    this.route.params.pipe(
      map((p => p.username))
    ).subscribe((username: String) => {
      this.api.getFeedbackHistory(username).subscribe((data: FeedbackHistoryPayload) => {
        this.data = data;
      });
    });
  }
}
