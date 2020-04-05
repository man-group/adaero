import { Component, Input, OnInit } from '@angular/core';
import { ApiService, EnrolleesPayload, MessageTemplatePayload } from '../../../services/api.service';
import { Observable } from 'rxjs';

@Component({
  selector: 'app-enrollees-list',
  templateUrl: './enrollees-list.component.html',
  styleUrls: ['./enrollees-list.component.scss']
})
export class EnrolleesListComponent implements OnInit {
    constructor(public api: ApiService) {}

    data: Observable<{} | EnrolleesPayload | MessageTemplatePayload>;

    ngOnInit() {
        this.data = this.api.getNominees();
    }
}
